from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends,
    HTTPException,
    status,
    File,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract, or_
import database as db
from datetime import datetime, UTC
import logging
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

from fastapi.responses import FileResponse
import os


@app.get("/baixar-leads")
def download_banco():
    if os.path.exists("crm.db"):
        return FileResponse(
            "crm.db", media_type="application/octet-stream", filename="leads_backup.db"
        )
    return {"erro": "Arquivo não encontrado"}


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Dependency
def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()


def get_notifications(db_session: Session):
    """Gera notificações baseadas em datas de projetos e status."""
    notifications = []

    # Usando a data local (sem timezone) para comparação com o banco SQLite
    today = datetime.now().date()

    # 1. Verifica TODOS os leads que possuem data final definida
    expired_leads = db_session.query(db.Lead).filter(db.Lead.end_date != None).all()

    for l in expired_leads:
        try:
            # Garante que temos um objeto date para comparação
            project_end_date = l.end_date.date()

            # Projeto atingiu a data final (hoje ou no passado)
            if project_end_date <= today:
                notifications.append(
                    {
                        "id": f"end-{l.id}",
                        "title": "Projeto Finalizado",
                        "message": f"O projeto de {l.name} ({l.company}) atingiu o prazo em {project_end_date.strftime('%d/%m/%Y')}.",
                        "type": "danger",
                        "link": "/clientes",
                    }
                )

            # Projeto finalizando nos próximos 7 dias
            else:
                days_left = (project_end_date - today).days
                if 0 < days_left <= 7:
                    notifications.append(
                        {
                            "id": f"warning-{l.id}",
                            "title": "Projeto Finalizando",
                            "message": f"O projeto de {l.name} termina em {days_left} dias.",
                            "type": "warning",
                            "link": "/clientes",
                        }
                    )
        except Exception as e:
            logger.error(f"Erro ao processar notificação para o lead {l.id}: {e}")

    return notifications


from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic(auto_error=False)


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )
    current_username_bytes = credentials.username.encode("utf8")

    # Busca o usuário no .env. Se der erro ou não achar o arquivo, usa "" (vazio) por segurança
    correct_username_bytes = os.getenv("LOGIN_USER", "").encode("utf8")

    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )

    current_password_bytes = credentials.password.encode("utf8")

    # Busca a senha no .env. Se der erro ou não achar o arquivo, usa "" (vazio) por segurança
    correct_password_bytes = os.getenv("LOGIN_PASSWORD", "").encode("utf8")

    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    leads = db_session.query(db.Lead).all()
    # No modelo atual, os resultados contabilizam o valor total de todos os leads (Pipeline)
    # para garantir que qualquer mudança de valor seja refletida no dashboard.

    # Métricas de conversão e totais
    total_leads = len(leads)
    leads_fechados_list = [l for l in leads if l.status == "Fechado"]
    total_clients = len(leads_fechados_list)
    conversion_rate = (total_clients / total_leads * 100) if total_leads > 0 else 0

    # Valor Total (Apenas leads com status 'Fechado')
    total_revenue = sum(l.value for l in leads_fechados_list if l.value)

    # Faturamento/Valor por mês para o gráfico (Apenas leads com status 'Fechado')
    from collections import defaultdict

    monthly_revenue_data = defaultdict(float)
    monthly_leads_count = defaultdict(int)

    for l in leads:
        # Contagem de leads por mês (usa data de criação) - Mantém todos os leads para o card de Leads
        if l.created_at:
            m_idx = l.created_at.month - 1
            monthly_leads_count[m_idx] += 1

        # Valor por mês (Apenas se o status for 'Fechado')
        if l.status == "Fechado" and l.value:
            # Tenta usar start_date, se não tiver usa created_at
            date_to_use = l.start_date or l.created_at
            if date_to_use:
                month_idx = date_to_use.month - 1  # 0-11
                monthly_revenue_data[month_idx] += l.value

    monthly_revenue = [monthly_revenue_data[i] for i in range(12)]
    monthly_leads = [monthly_leads_count[i] for i in range(12)]

    # Valor e Volume por tipo de projeto (Apenas leads com status 'Fechado')
    # 1. Define os serviços principais e inicializa os tipos
    servicos_principais = ["Posicionamento", "Consultoria", "Marca autêntica"]
    all_project_types = servicos_principais + ["Outros serviços"]

    # 2. Inicializa os dicionários zerados
    revenue_by_type = {pt: 0.0 for pt in all_project_types}
    volume_by_type = {pt: 0 for pt in all_project_types}
    type_details = {
        pt: {"total": 0, "fechados": 0, "perdidos": 0} for pt in all_project_types
    }

    # 3. Calcula volume, faturamento e detalhes (Agrupando em Outros Serviços)
    for l in leads:
        # Se não for principal, vira "Outros serviços"
        chave = (
            l.project_type
            if l.project_type in servicos_principais
            else "Outros serviços"
        )

        type_details[chave]["total"] += 1

        if l.status == "Fechado":
            type_details[chave]["fechados"] += 1
            volume_by_type[chave] += 1
            if l.value:
                revenue_by_type[chave] += l.value
        elif l.status == "Não fechou":
            type_details[chave]["perdidos"] += 1

    # 4. Taxa de conversão agrupada
    conversion_by_type = {}
    for pt in all_project_types:
        if type_details[pt]["total"] > 0:
            conversion_by_type[pt] = round(
                (type_details[pt]["fechados"] / type_details[pt]["total"]) * 100, 1
            )
        else:
            conversion_by_type[pt] = 0
    # Métricas de conversão
    leads_fechados = len(leads_fechados_list)
    leads_perdidos = len([l for l in leads if l.status == "Não fechou"])
    leads_em_aberto = len(
        [l for l in leads if l.status not in ["Fechado", "Não fechou"]]
    )

    # Notificações unificadas
    notifications = get_notifications(db_session)
    now = datetime.now()

    logger.info(
        f"DASHBOARD: Enviando {len(notifications)} notificações para o template."
    )

    # Calendário de Projetos/Leads por mês
    calendar_data = defaultdict(list)
    for l in leads:
        date_to_use = l.start_date or l.created_at
        if date_to_use:
            m_idx = date_to_use.month - 1
            calendar_data[m_idx].append(
                {
                    "id": l.id,
                    "name": l.name,
                    "company": l.company,
                    "status": l.status,
                    "photo": l.photo_path or f"https://i.pravatar.cc/100?u={l.id}",
                }
            )

    # Prepara dados do calendário para o template (garante todos os 12 meses)
    full_calendar_data = []
    month_names = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    for i in range(12):
        full_calendar_data.append(
            {"name": month_names[i], "items": list(calendar_data[i])}
        )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "total_leads": total_leads,
            "total_clients": total_clients,
            "conversion_rate": round(conversion_rate, 1),
            "total_revenue": total_revenue,
            "revenue_by_type": revenue_by_type,
            "volume_by_type": volume_by_type,
            "conversion_by_type": conversion_by_type,
            "type_details": type_details,
            "leads_fechados": leads_fechados,
            "leads_perdidos": leads_perdidos,
            "leads": leads,
            "monthly_revenue": monthly_revenue,
            "monthly_leads": monthly_leads,
            "notifications": notifications,
            "now": now,
            "full_calendar": full_calendar_data,
        },
    )


@app.get("/vendas", response_class=HTMLResponse)
async def vendas(
    request: Request,
    filter: str = "all",
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    query = db_session.query(db.Lead)

    if filter == "month":
        now = datetime.now()
        query = query.filter(
            extract("month", db.Lead.created_at) == now.month,
            extract("year", db.Lead.created_at) == now.year,
        )

    leads = query.all()
    notifications = get_notifications(db_session)

    return templates.TemplateResponse(
        request,
        "vendas.html",
        {"leads": leads, "notifications": notifications, "current_filter": filter},
    )


@app.get("/clientes", response_class=HTMLResponse)
async def clientes(
    request: Request,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    clients = db_session.query(db.Lead).filter(db.Lead.status == "Fechado").all()
    notifications = get_notifications(db_session)

    return templates.TemplateResponse(
        request, "clientes.html", {"clients": clients, "notifications": notifications}
    )


UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_photo(photo: UploadFile):
    if not photo or not photo.filename:
        return None

    file_extension = os.path.splitext(photo.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    return f"/static/uploads/{file_name}"


@app.middleware("http")
async def check_projects_middleware(request: Request, call_next):
    """Middleware que verifica projetos finalizados e atualiza status se necessário."""
    if request.method == "GET":
        db_session = db.SessionLocal()
        try:
            today = datetime.now().date()
            # Busca qualquer lead que tenha data final atingida mas ainda não esteja formalmente "Fechado"
            # ou que precise de uma marcação de finalizado.
            # Seguindo a instrução: "marcado como fechado e movido para a aba de clientes"
            expired_leads = (
                db_session.query(db.Lead)
                .filter(db.Lead.status != "Fechado", db.Lead.end_date != None)
                .all()
            )

            for p in expired_leads:
                if p.end_date.date() <= today:
                    p.status = "Fechado"
                    logger.info(
                        f"AUTO-MOVE: Lead {p.name} movido para 'Fechado' pois atingiu a data final ({p.end_date})."
                    )

            db_session.commit()
        except Exception as e:
            logger.error(f"Erro no middleware de checagem: {e}")
            db_session.rollback()
        finally:
            db_session.close()

    response = await call_next(request)
    return response


import uuid
import shutil


@app.post("/add_lead")
async def add_lead(
    name: str = Form(...),
    company: str = Form(None),
    social_media: str = Form(None),
    phone: str = Form(None),
    status: str = Form("Lead"),
    temperature: str = Form("Morno"),
    project_type: str = Form("Marca autêntica"),
    value: float = Form(0.0),
    photo: UploadFile = File(None),
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    photo_path = await save_photo(photo)
    new_lead = db.Lead(
        name=name,
        company=company,
        social_media=social_media,
        phone=phone,
        status=status,
        temperature=temperature,
        project_type=project_type,
        value=value,
        photo_path=photo_path,
    )
    db_session.add(new_lead)
    db_session.commit()
    return RedirectResponse(url="/vendas", status_code=303)


@app.post("/update_lead/{lead_id}")
async def update_lead(
    request: Request,
    lead_id: int,
    name: str = Form(None),
    company: str = Form(None),
    social_media: str = Form(None),
    phone: str = Form(None),
    status: str = Form(None),
    temperature: str = Form(None),
    project_type: str = Form(None),
    value: float = Form(None),
    problems: str = Form(None),
    solutions: str = Form(None),
    observations: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    scope: str = Form(None),
    photo: UploadFile = File(None),
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    lead = (
        db_session.query(db.Lead)
        .filter(db.Lead.id == lead_id)
        .with_for_update()
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if name is not None:
        lead.name = name
    if company is not None:
        lead.company = company
    if social_media is not None:
        lead.social_media = social_media
    if phone is not None:
        lead.phone = phone
    if temperature is not None:
        lead.temperature = temperature
    if project_type is not None:
        lead.project_type = project_type
    if value is not None:
        lead.value = value
    if problems is not None:
        lead.problems = problems
    if solutions is not None:
        lead.solutions = solutions
    if observations is not None:
        lead.observations = observations
    if scope is not None:
        lead.scope = scope

    if start_date:
        try:
            lead.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except Exception:
            pass
    if end_date:
        try:
            lead.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except Exception:
            pass

    new_photo = await save_photo(photo)
    if new_photo:
        lead.photo_path = new_photo

    if status is not None:
        lead.status = status

    db_session.commit()

    # Redireciona com base no referer para manter o usuário na mesma aba
    referer = request.headers.get("referer")
    if referer and "/clientes" in referer:
        return RedirectResponse(url="/clientes", status_code=303)
    return RedirectResponse(url="/vendas", status_code=303)


@app.post("/delete_lead/{lead_id}")
async def delete_lead(
    request: Request,
    lead_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    lead = db_session.query(db.Lead).filter(db.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 1. Busca o quadro Kanban associado a este lead
    board = (
        db_session.query(db.KanbanBoard)
        .filter(db.KanbanBoard.lead_id == lead_id)
        .first()
    )

    if board:
        # 2. Busca todas as listas do quadro
        lists = (
            db_session.query(db.KanbanList)
            .filter(db.KanbanList.board_id == board.id)
            .all()
        )
        for lst in lists:
            # 3. Busca todos os cartões da lista
            cards = (
                db_session.query(db.KanbanCard)
                .filter(db.KanbanCard.list_id == lst.id)
                .all()
            )
            for card in cards:
                # 4. Deleta arquivos físicos vinculados ao cartão para não lotar o servidor
                if card.file_path and os.path.exists(card.file_path.lstrip("/")):
                    os.remove(card.file_path.lstrip("/"))
                db_session.delete(card)

            # Deleta a lista
            db_session.delete(lst)

        # Deleta o quadro
        db_session.delete(board)

    # 5. Agora que as dependências do Kanban sumiram, deletamos o lead
    db_session.delete(lead)
    db_session.commit()

    # Redireciona de volta para onde o usuário estava
    referer = request.headers.get("referer")
    if referer and "/clientes" in referer:
        return RedirectResponse(url="/clientes", status_code=303)
    return RedirectResponse(url="/vendas", status_code=303)


@app.post("/restore_lead")
async def restore_lead(
    name: str = Form(...),
    company: str = Form(None),
    status: str = Form(...),
    value: float = Form(0.0),
    project_type: str = Form(None),
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    # This is a simplified restore. In a real app, we'd use a soft-delete (deleted_at)
    new_lead = db.Lead(
        name=name,
        company=company,
        status=status,
        value=value,
        project_type=project_type,
    )
    db_session.add(new_lead)
    db_session.commit()
    return {"status": "success"}


# --- Kanban Routes ---


@app.get("/cliente/{lead_id}/kanban", response_class=HTMLResponse)
async def cliente_kanban(
    request: Request,
    lead_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    lead = db_session.query(db.Lead).filter(db.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get or create board
    board = (
        db_session.query(db.KanbanBoard)
        .filter(db.KanbanBoard.lead_id == lead_id)
        .first()
    )
    if not board:
        board = db.KanbanBoard(lead_id=lead_id)
        db_session.add(board)
        db_session.commit()
        db_session.refresh(board)

        # Create default lists
        default_lists = ["Demandas a iniciar", "Em execução", "Concluídas"]
        for i, list_name in enumerate(default_lists):
            new_list = db.KanbanList(board_id=board.id, name=list_name, order_index=i)
            db_session.add(new_list)
        db_session.commit()

    # Get all lists and cards for this board
    lists = (
        db_session.query(db.KanbanList)
        .filter(db.KanbanList.board_id == board.id)
        .order_by(db.KanbanList.order_index)
        .all()
    )
    list_data = []
    for lst in lists:
        cards = (
            db_session.query(db.KanbanCard)
            .filter(db.KanbanCard.list_id == lst.id)
            .order_by(db.KanbanCard.order_index)
            .all()
        )
        list_data.append(
            {
                "id": lst.id,
                "name": lst.name,
                "order_index": lst.order_index,
                "cards": cards,
            }
        )

    notifications = get_notifications(db_session)
    return templates.TemplateResponse(
        request,
        "kanban.html",
        {
            "lead": lead,
            "board": board,
            "lists": list_data,
            "notifications": notifications,
        },
    )


@app.post("/cliente/{lead_id}/kanban/add-lista")
async def add_kanban_list(
    request: Request,
    lead_id: int,
    name: str = Form(...),
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    board = (
        db_session.query(db.KanbanBoard)
        .filter(db.KanbanBoard.lead_id == lead_id)
        .first()
    )
    if not board:
        # Create board if doesn't exist
        board = db.KanbanBoard(lead_id=lead_id)
        db_session.add(board)
        db_session.commit()
        db_session.refresh(board)

    max_order = (
        db_session.query(db.KanbanList)
        .filter(db.KanbanList.board_id == board.id)
        .count()
    )
    new_list = db.KanbanList(board_id=board.id, name=name, order_index=max_order)
    db_session.add(new_list)
    db_session.commit()
    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/lista/{list_id}/edit")
async def edit_kanban_list(
    request: Request,
    lead_id: int,
    list_id: int,
    name: str = Form(...),
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    lst = db_session.query(db.KanbanList).filter(db.KanbanList.id == list_id).first()
    if lst:
        lst.name = name
        db_session.commit()
    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/lista/{list_id}/delete")
async def delete_kanban_list(
    request: Request,
    lead_id: int,
    list_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    lst = db_session.query(db.KanbanList).filter(db.KanbanList.id == list_id).first()
    if lst:
        # Delete all cards first
        cards = (
            db_session.query(db.KanbanCard)
            .filter(db.KanbanCard.list_id == list_id)
            .all()
        )
        for card in cards:
            if card.file_path and os.path.exists(card.file_path.lstrip("/")):
                os.remove(card.file_path.lstrip("/"))
            db_session.delete(card)
        db_session.delete(lst)
        db_session.commit()
    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/lista/{list_id}/add-card")
async def add_kanban_card(
    request: Request,
    lead_id: int,
    list_id: int,
    title: str = Form(...),
    description: str = Form(None),
    color: str = Form("#ffffff"),
    link: str = Form(None),
    file: UploadFile = File(None),
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    file_path = None
    if file and file.filename:
        file_path = await save_photo(file)

    max_order = (
        db_session.query(db.KanbanCard).filter(db.KanbanCard.list_id == list_id).count()
    )
    new_card = db.KanbanCard(
        list_id=list_id,
        title=title,
        description=description,
        color=color,
        link=link,
        file_path=file_path,
        order_index=max_order,
    )
    db_session.add(new_card)
    db_session.commit()
    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/card/{card_id}/edit")
async def edit_kanban_card(
    request: Request,
    lead_id: int,
    card_id: int,
    title: str = Form(...),
    description: str = Form(None),
    color: str = Form("#ffffff"),
    link: str = Form(None),
    file: UploadFile = File(None),
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    card = db_session.query(db.KanbanCard).filter(db.KanbanCard.id == card_id).first()
    if card:
        card.title = title
        card.description = description
        card.color = color
        card.link = link

        if file and file.filename:
            if card.file_path and os.path.exists(card.file_path.lstrip("/")):
                os.remove(card.file_path.lstrip("/"))
            card.file_path = await save_photo(file)

        db_session.commit()
    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/card/{card_id}/toggle-complete")
async def toggle_kanban_card_complete(
    request: Request,
    lead_id: int,
    card_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    card = db_session.query(db.KanbanCard).filter(db.KanbanCard.id == card_id).first()
    if card:
        # Toggle completion
        card.is_completed = 1 - card.is_completed

        # Get the board
        board = (
            db_session.query(db.KanbanBoard)
            .filter(db.KanbanBoard.lead_id == lead_id)
            .first()
        )

        if card.is_completed == 1:
            # Move to Concluídas
            done_list = (
                db_session.query(db.KanbanList)
                .filter(
                    db.KanbanList.board_id == board.id,
                    db.KanbanList.name == "Concluídas",
                )
                .first()
            )

            if not done_list:
                max_order = (
                    db_session.query(db.KanbanList)
                    .filter(db.KanbanList.board_id == board.id)
                    .count()
                )
                done_list = db.KanbanList(
                    board_id=board.id, name="Concluídas", order_index=max_order
                )
                db_session.add(done_list)
                db_session.commit()
                db_session.refresh(done_list)

            card.list_id = done_list.id
            max_card_order = (
                db_session.query(db.KanbanCard)
                .filter(db.KanbanCard.list_id == done_list.id)
                .count()
            )
            card.order_index = max_card_order
        else:
            # Move back to Demandas a Iniciar
            start_list = (
                db_session.query(db.KanbanList)
                .filter(
                    db.KanbanList.board_id == board.id,
                    db.KanbanList.name == "Demandas a iniciar",
                )
                .first()
            )

            if not start_list:
                # If no "Demandas a iniciar", use first list
                start_list = (
                    db_session.query(db.KanbanList)
                    .filter(db.KanbanList.board_id == board.id)
                    .order_by(db.KanbanList.order_index)
                    .first()
                )

            if start_list:
                card.list_id = start_list.id
                max_card_order = (
                    db_session.query(db.KanbanCard)
                    .filter(db.KanbanCard.list_id == start_list.id)
                    .count()
                )
                card.order_index = max_card_order

        db_session.commit()

    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/card/{card_id}/delete")
async def delete_kanban_card(
    request: Request,
    lead_id: int,
    card_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    card = db_session.query(db.KanbanCard).filter(db.KanbanCard.id == card_id).first()
    if card:
        if card.file_path and os.path.exists(card.file_path.lstrip("/")):
            os.remove(card.file_path.lstrip("/"))
        db_session.delete(card)
        db_session.commit()
    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/card/{card_id}/move/{new_list_id}")
async def move_kanban_card(
    request: Request,
    lead_id: int,
    card_id: int,
    new_list_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    card = db_session.query(db.KanbanCard).filter(db.KanbanCard.id == card_id).first()
    if card:
        # --- NOVA LÓGICA DE MARCAR/DESMARCAR ---
        nova_lista = (
            db_session.query(db.KanbanList)
            .filter(db.KanbanList.id == new_list_id)
            .first()
        )
        if nova_lista:
            nome_lista = nova_lista.name.strip().lower()
            if nome_lista in ["demandas a iniciar", "em execução"]:
                card.is_completed = 0
            elif nome_lista == "concluídas":
                card.is_completed = 1
        # ---------------------------------------

        card.list_id = new_list_id
        max_order = (
            db_session.query(db.KanbanCard)
            .filter(db.KanbanCard.list_id == new_list_id)
            .count()
        )
        card.order_index = max_order
        db_session.commit()
    return RedirectResponse(url=f"/cliente/{lead_id}/kanban", status_code=303)


@app.post("/cliente/{lead_id}/kanban/reorder")
async def reorder_kanban_cards(
    request: Request,
    lead_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    form_data = await request.form()
    card_order = form_data.getlist("card_order[]")
    list_id = int(form_data.get("list_id"))

    # --- NOVA LÓGICA PARA O DRAG AND DROP ---
    nova_lista = (
        db_session.query(db.KanbanList).filter(db.KanbanList.id == list_id).first()
    )
    status_conclusao = None

    if nova_lista:
        nome_lista = nova_lista.name.strip().lower()
        if nome_lista in ["demandas a iniciar", "em execução"]:
            status_conclusao = 0
        elif nome_lista == "concluídas":
            status_conclusao = 1
    # ----------------------------------------

    for i, card_id in enumerate(card_order):
        card = (
            db_session.query(db.KanbanCard)
            .filter(db.KanbanCard.id == int(card_id))
            .first()
        )
        if card:
            card.order_index = i
            card.list_id = list_id

            # Aplica o status de conclusão se o cartão mudou para uma dessas listas
            if status_conclusao is not None:
                card.is_completed = status_conclusao

    db_session.commit()
    return {"status": "ok"}


@app.post("/cliente/{lead_id}/kanban/reorder-lists")
async def reorder_kanban_lists(
    request: Request,
    lead_id: int,
    db_session: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    form_data = await request.form()
    list_order = form_data.getlist("list_order[]")

    for i, list_id in enumerate(list_order):
        lst = (
            db_session.query(db.KanbanList)
            .filter(db.KanbanList.id == int(list_id))
            .first()
        )
        if lst:
            lst.order_index = i

    db_session.commit()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
