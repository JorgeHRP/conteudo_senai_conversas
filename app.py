from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
from dotenv import load_dotenv
from functools import wraps
from datetime import datetime
import os
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "senai-secret-2024")

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

LOGIN_USER = os.getenv("LOGIN_USER", "admin")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "puc2026")

STATUS_MAP = {
    1: {"label": "Lead Novo",      "color": "#0071e3", "bg": "rgba(0,113,227,0.18)"},
    2: {"label": "Interesse",      "color": "#34c759", "bg": "rgba(52,199,89,0.18)"},
    3: {"label": "Sem Interesse",  "color": "#ff3b30", "bg": "rgba(255,59,48,0.18)"},
}
PENDING_STATUS = {"label": "Pendente", "color": "#8e8e93", "bg": "rgba(142,142,147,0.18)"}

# Dados mocados apenas para demonstracao da tela de criacao de agentes
MOCK_AGENTS = [
    {
        "nome": "SDR SENAI - Captacao",
        "modelo": "GPT-4o mini",
        "tom": "Consultivo",
        "temperatura": 0.7,
        "status": "ativo",
        "conversas": 482,
        "taxa_resposta": 94,
        "base_conhecimento": "cursos_senai_2026.csv",
        "criado_em": "18/02/2026",
    },
    {
        "nome": "Suporte Matriculas",
        "modelo": "Claude 3.5 Sonnet",
        "tom": "Formal",
        "temperatura": 0.4,
        "status": "ativo",
        "conversas": 216,
        "taxa_resposta": 98,
        "base_conhecimento": "faq_matriculas.csv",
        "criado_em": "02/04/2026",
    },
    {
        "nome": "Follow-up Pos-Venda",
        "modelo": "GPT-4o",
        "tom": "Casual e Amigavel",
        "temperatura": 0.9,
        "status": "pausado",
        "conversas": 63,
        "taxa_resposta": 81,
        "base_conhecimento": "roteiro_followup.csv",
        "criado_em": "27/05/2026",
    },
]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == LOGIN_USER and password == LOGIN_PASSWORD:
            session["logged_in"] = True
            session.permanent = True
            return redirect(url_for("dashboard"))
        error = "Usuário ou senha incorretos"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    users = supabase.table("conteudo_senai_usuario").select("*").execute().data or []

    total = len(users)
    status_counts = {1: 0, 2: 0, 3: 0}
    follow_sim = 0
    follow_nao = 0
    date_groups = {}

    for u in users:
        raw = u.get("status")
        s = int(raw) if raw is not None else None
        if s in status_counts:
            status_counts[s] += 1

        if u.get("follow_up"):
            follow_sim += 1
        else:
            follow_nao += 1

        dt_str = u.get("created_at", "")
        if dt_str:
            date_key = dt_str[:10]
            date_groups[date_key] = date_groups.get(date_key, 0) + 1

    dates = sorted(date_groups.keys())
    date_counts = [date_groups[d] for d in dates]
    dates_display = []
    for d in dates:
        try:
            dates_display.append(datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m"))
        except Exception:
            dates_display.append(d)

    sem_status = total - sum(status_counts.values())
    taxa_interesse = round((status_counts[2] / total * 100) if total else 0, 1)

    return render_template(
        "dashboard.html",
        active_tab="dashboard",
        total=total,
        lead_novo=status_counts[1],
        interesse=status_counts[2],
        sem_interesse=status_counts[3],
        sem_status=sem_status,
        follow_sim=follow_sim,
        follow_nao=follow_nao,
        taxa_interesse=taxa_interesse,
        dates=json.dumps(dates_display),
        date_counts=json.dumps(date_counts),
    )


@app.route("/atendimentos")
@login_required
def atendimentos():
    users = (
        supabase.table("conteudo_senai_usuario")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    for u in users:
        raw = u.get("status")
        s = int(raw) if raw is not None else None
        info = STATUS_MAP.get(s, PENDING_STATUS)
        u["status_label"] = info["label"]
        u["status_color"] = info["color"]
        u["status_bg"] = info["bg"]
        u["status_key"] = str(s) if s is not None else "none"
        u["follow_up_label"] = "Sim" if u.get("follow_up") else "Nao"
        dt = u.get("created_at", "")
        if dt:
            try:
                u["created_formatted"] = datetime.fromisoformat(
                    dt.replace("Z", "+00:00")
                ).strftime("%d/%m/%Y %H:%M")
            except Exception:
                u["created_formatted"] = dt[:16]
        else:
            u["created_formatted"] = "—"

    return render_template("atendimentos.html", users=users, active_tab="atendimentos")


@app.route("/agentes")
@login_required
def agentes():
    return render_template("agentes.html", active_tab="agentes", agents=MOCK_AGENTS)


@app.route("/api/conversation/<telefone>")
@login_required
def get_conversation(telefone):
    rows = (
        supabase.table("conteudo_senai_conversas")
        .select("*")
        .eq("session_id", telefone)
        .order("id")
        .execute()
        .data or []
    )
    messages = []
    for row in rows:
        msg = row.get("message", {})
        if isinstance(msg, str):
            try:
                msg = json.loads(msg)
            except Exception:
                msg = {}
        content = msg.get("content", "")
        if not content:
            continue
        # AI responses may carry a JSON payload — extract only the human-readable part
        if isinstance(content, str) and content.strip().startswith("{"):
            try:
                parsed = json.loads(content)
                mensagem = (
                    parsed.get("output", {}).get("mensagem")
                    or parsed.get("mensagem")
                    or content
                )
                content = mensagem
            except Exception:
                pass
        messages.append({"type": msg.get("type", "unknown"), "content": content})
    return jsonify(messages)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
