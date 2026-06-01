from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract, or_
import database as db
from datetime import datetime, UTC
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

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
                notifications.append({
                    "id": f"end-{l.id}",
                    "title": "Projeto Finalizado",
                    "message": f"O projeto de {l.name} ({l.company}) atingiu o prazo em {project_end_date.strftime('%d/%m/%Y')}.",
                    "type": "danger",
                    "link": "/clientes"
                })
            
            # Projeto finalizando nos próximos 7 dias
            else:
                days_left = (project_end_date - today).days
                if 0 < days_left <= 7:
                    notifications.append({
                        "id": f"warning-{l.id}",
                        "title": "Projeto Finalizando",
                        "message": f"O projeto de {l.name} termina em {days_left} dias.",
                        "type": "warning",
                        "link": "/clientes"
                    })
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
    correct_username_bytes = b"admin"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"trazzo2026"
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
async def dashboard(request: Request, db_session: Session = Depends(get_db), user: str = Depends(get_current_user)):
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
                month_idx = date_to_use.month - 1 # 0-11
                monthly_revenue_data[month_idx] += l.value
            
    monthly_revenue = [monthly_revenue_data[i] for i in range(12)]
    monthly_leads = [monthly_leads_count[i] for i in range(12)]
    
    # Valor e Volume por tipo de projeto (Apenas leads com status 'Fechado')
    revenue_by_type = {
        "Marca autêntica": sum(l.value for l in leads_fechados_list if l.project_type == "Marca autêntica" and l.value),
        "Posicionamento": sum(l.value for l in leads_fechados_list if l.project_type == "Posicionamento" and l.value),
        "Consultoria": sum(l.value for l in leads_fechados_list if l.project_type == "Consultoria" and l.value)
    }
    
    volume_by_type = {
        "Marca autêntica": len([l for l in leads_fechados_list if l.project_type == "Marca autêntica"]),
        "Posicionamento": len([l for l in leads_fechados_list if l.project_type == "Posicionamento"]),
        "Consultoria": len([l for l in leads_fechados_list if l.project_type == "Consultoria"])
    }
    
    # Métricas de conversão
    leads_fechados = len(leads_fechados_list)
    leads_perdidos = len([l for l in leads if l.status == "Não fechou"])
    leads_em_aberto = len([l for l in leads if l.status not in ["Fechado", "Não fechou"]])
    
    # Notificações unificadas
    notifications = get_notifications(db_session)
    now = datetime.now()
    
    logger.info(f"DASHBOARD: Enviando {len(notifications)} notificações para o template.")
    
    # Calendário de Projetos/Leads por mês
    calendar_data = defaultdict(list)
    for l in leads:
        date_to_use = l.start_date or l.created_at
        if date_to_use:
            m_idx = date_to_use.month - 1
            calendar_data[m_idx].append({
                "id": l.id,
                "name": l.name,
                "company": l.company,
                "status": l.status,
                "photo": l.photo_path or f"https://i.pravatar.cc/100?u={l.id}"
            })
    
    # Prepara dados do calendário para o template (garante todos os 12 meses)
    full_calendar_data = []
    month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    for i in range(12):
        full_calendar_data.append({
            "name": month_names[i],
            "items": list(calendar_data[i])
        })
    
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
            "leads_fechados": leads_fechados,
            "leads_perdidos": leads_perdidos,
            "leads": leads,
            "monthly_revenue": monthly_revenue,
            "monthly_leads": monthly_leads,
            "notifications": notifications,
            "now": now,
            "full_calendar": full_calendar_data
        }
    )

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(request: Request, filter: str = "all", db_session: Session = Depends(get_db), user: str = Depends(get_current_user)):
    query = db_session.query(db.Lead)
    
    if filter == "month":
        now = datetime.now()
        query = query.filter(
            extract('month', db.Lead.created_at) == now.month,
            extract('year', db.Lead.created_at) == now.year
        )
        
    leads = query.all()
    notifications = get_notifications(db_session)
    
    return templates.TemplateResponse(
        request,
        "vendas.html",
        {"leads": leads, "notifications": notifications, "current_filter": filter}
    )

@app.get("/clientes", response_class=HTMLResponse)
async def clientes(request: Request, db_session: Session = Depends(get_db), user: str = Depends(get_current_user)):
    clients = db_session.query(db.Lead).filter(db.Lead.status == "Fechado").all()
    notifications = get_notifications(db_session)
    
    return templates.TemplateResponse(
        request,
        "clientes.html",
        {"clients": clients, "notifications": notifications}
    )

import os
import uuid
import shutil

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
            expired_leads = db_session.query(db.Lead).filter(
                db.Lead.status != "Fechado",
                db.Lead.end_date != None
            ).all()
            
            for p in expired_leads:
                if p.end_date.date() <= today:
                    p.status = "Fechado"
                    logger.info(f"AUTO-MOVE: Lead {p.name} movido para 'Fechado' pois atingiu a data final ({p.end_date}).")
            
            db_session.commit()
        except Exception as e:
            logger.error(f"Erro no middleware de checagem: {e}")
            db_session.rollback()
        finally:
            db_session.close()
            
    response = await call_next(request)
    return response

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
    user: str = Depends(get_current_user)
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
        photo_path=photo_path
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
    user: str = Depends(get_current_user)
):
    lead = db_session.query(db.Lead).filter(db.Lead.id == lead_id).with_for_update().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if name is not None: lead.name = name
    if company is not None: lead.company = company
    if social_media is not None: lead.social_media = social_media
    if phone is not None: lead.phone = phone
    if temperature is not None: lead.temperature = temperature
    if project_type is not None: lead.project_type = project_type
    if value is not None: lead.value = value
    if problems is not None: lead.problems = problems
    if solutions is not None: lead.solutions = solutions
    if observations is not None: lead.observations = observations
    if scope is not None: lead.scope = scope
    
    if start_date:
        try:
            lead.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        except Exception:
            pass
    if end_date:
        try:
            lead.end_date = datetime.strptime(end_date, '%Y-%m-%d')
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
    user: str = Depends(get_current_user)
):
    lead = db_session.query(db.Lead).filter(db.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
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
    user: str = Depends(get_current_user)
):
    # This is a simplified restore. In a real app, we'd use a soft-delete (deleted_at)
    new_lead = db.Lead(
        name=name,
        company=company,
        status=status,
        value=value,
        project_type=project_type
    )
    db_session.add(new_lead)
    db_session.commit()
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
