import os, json, csv
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from dotenv import load_dotenv

load_dotenv('/app/.env')
AGENT_TOKEN = os.getenv('AGENT_TOKEN', 'jensen4254')

DATA_PATH = '/app/data'
CONV_FILE = f'{DATA_PATH}/conversations.json'

router = APIRouter()

def load_conversations():
    if not os.path.exists(CONV_FILE):
        return []
    with open(CONV_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

@router.get("/exports/conversations")
def export_conversations(format: str = 'json', x_agent_token: str = Header(None)):
    if x_agent_token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = load_conversations()

    if format == 'json':
        return JSONResponse(content=data)

    if format == 'csv':
        csv_path = f'{DATA_PATH}/conversations_export.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id','route','summary','user_message','assistant_message']
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for c in data:
                um = " | ".join([m.get('content','') for m in c.get('messages',[]) if m.get('role')=='user'])
                am = " | ".join([m.get('content','') for m in c.get('messages',[]) if m.get('role')=='assistant'])
                w.writerow({
                    'id': c.get('id',''),
                    'route': c.get('route',''),
                    'summary': c.get('summary',''),
                    'user_message': um,
                    'assistant_message': am
                })
        return FileResponse(csv_path, media_type='text/csv', filename='conversations_export.csv')

    raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")
