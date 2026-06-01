from database import SessionLocal, Lead, Client
from datetime import datetime

def populate():
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(Lead).first():
        print("Data already exists. Skipping population.")
        return

    leads = [
        Lead(name="André da barraquinha", company="barraca do andré", social_media="andrebarraca", phone="(31) 98989 8989", status="Lead", temperature="Quente", problems="Baixo faturamento na barraca de pastéis", solutions="Marca autêntica", project_type="Marca autêntica", value=5000),
        Lead(name="Leonardo antunes", company="Sky Fit Andradas", social_media="skyfitbhandradas", phone="(31) 98989 8989", status="Negociação", temperature="Quente", problems="Precisa de uma nova idv, está rompendo com a empresa antiga...", solutions="Projeto de marca completo + acompanhamento", project_type="Posicionamento", value=20000),
        Lead(name="Giovanna Menezes", company="Boing fitness", social_media="boingfitness", phone="(31) 98989 8989", status="Não fechou", temperature="Morno", problems="Posicionamento ruim, nome não registrável", solutions="Projeto de marca autêntica", project_type="Marca autêntica", value=15000),
        Lead(name="Alessandra Pereira", company="Alessandra dogs", social_media="dogandra", phone="(31) 98989 8989", status="Fechado", temperature="Quente", project_type="Consultoria", value=12000),
    ]
    
    db.add_all(leads)
    db.commit()
    
    # Convert "Fechado" to Client
    fechado = db.query(Lead).filter(Lead.status == "Fechado").first()
    if fechado:
        client = Client(
            name=fechado.name,
            company=fechado.company,
            social_media=fechado.social_media,
            phone=fechado.phone,
            project_type=fechado.project_type,
            value=fechado.value,
            lead_id=fechado.id,
            scope="Projeto de consultoria para expansão de marca."
        )
        db.add(client)
        db.commit()

    print("Sample data populated.")
    db.close()

if __name__ == "__main__":
    populate()
