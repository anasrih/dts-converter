import os
import asyncio
import datetime
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import subprocess
from typing import List, Dict, Optional
import uuid
import requests

app = FastAPI(title="API de conversion DTS vers EAC3")

# Base de données en mémoire pour suivre les conversions
conversions = {}

# Configuration Telegram
TELEGRAM_BOT_TOKEN = "YOUR TELEGRAM TOKEN"
TELEGRAM_CHAT_ID = "YOUR CHAT ID"
SEND_TELEGRAM_NOTIFICATION = "N"  # Initialisée à "N", changer en "O" pour envoyer des notifications

class VideoPath(BaseModel):
    path: str

class ConversionStatus(BaseModel):
    id: str
    filename: str
    start_time: str
    end_time: Optional[str] = None
    status: str
    elapsed_time: str

async def is_video_file(file_path: str) -> bool:
    """Vérifie si le fichier est une vidéo en utilisant ffprobe."""
    if not os.path.isfile(file_path):
        return False
    
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            file_path
        ]
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        data = json.loads(stdout)
        streams = data.get("streams", [])
        
        return any(stream.get("codec_type") == "video" for stream in streams)
    except Exception:
        return False

async def get_dts_tracks(file_path: str) -> List[Dict]:
    """Identifie les pistes DTS dans le fichier vidéo."""
    dts_tracks = []
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=index:stream=codec_name:stream=bit_rate:stream=codec_type",
        "-of", "json",
        file_path
    ]
    
    result = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await result.communicate()
    
    data = json.loads(stdout)
    streams = data.get("streams", [])
    
    for stream in streams:
        codec_name = stream.get("codec_name", "").lower()
        codec_type = stream.get("codec_type", "").lower()
        
        if codec_type == "audio" and "dts" in codec_name:
            bit_rate = stream.get("bit_rate")
            # Si le débit n'est pas spécifié, utiliser 768k
            if not bit_rate:
                bit_rate = "768000"
            
            dts_tracks.append({
                "index": stream.get("index"),
                "bit_rate": bit_rate
            })
    
    return dts_tracks

def send_telegram_message(message: str, parse_mode: str = "HTML"):
    """Envoie un message Telegram."""
    if SEND_TELEGRAM_NOTIFICATION != "O":
        return  # Ne pas envoyer le message si SEND_TELEGRAM_NOTIFICATION n'est pas "O"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'envoi du message Telegram: {e}")

async def convert_dts_to_eac3(file_path: str, conversion_id: str) -> None:
    """Convertit les pistes DTS en EAC3 en conservant le débit original."""
    try:
        # Mettre à jour le statut
        conversions[conversion_id]["status"] = "En cours"
        
        # Vérifier si c'est un fichier vidéo
        if not await is_video_file(file_path):
            conversions[conversion_id]["status"] = "Échec - Pas un fichier vidéo"
            conversions[conversion_id]["end_time"] = datetime.datetime.now()
            send_telegram_message(f"<b>Conversion terminée</b> pour <code>{file_path}</code>: Pas un fichier vidéo")
            return
        
        # Identifier les pistes DTS
        dts_tracks = await get_dts_tracks(file_path)
        
        if not dts_tracks:
            conversions[conversion_id]["status"] = "Terminé - Aucune piste DTS trouvée"
            conversions[conversion_id]["end_time"] = datetime.datetime.now()
            send_telegram_message(f"<b>Conversion terminée</b> pour <code>{file_path}</code>: Aucune piste DTS trouvée")
            return
        
        # Créer un fichier de sortie temporaire
        dir_name, file_name = os.path.split(file_path)
        base_name, ext = os.path.splitext(file_name)
        output_file = os.path.join(dir_name, f"{base_name}_eac3{ext}")
        
        # Obtenir toutes les informations sur les flux
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=index:stream=codec_name:stream=codec_type",
            "-of", "json",
            file_path
        ]
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        data = json.loads(stdout)
        streams = data.get("streams", [])
        
        # Préparer les options de conversion
        ffmpeg_cmd = ["ffmpeg", "-i", file_path]

        map_count = 0

        # Mapper tous les flux
        for stream in streams:
            stream_index = stream.get("index")
            codec_name = stream.get("codec_name", "").lower()
            codec_type = stream.get("codec_type", "").lower()
            
            # Mapper ce flux
            ffmpeg_cmd.extend(["-map", f"0:{stream_index}"])
            
            # Si c'est une piste DTS audio, la convertir en EAC3
            if codec_type == "audio":
                dts_track = next((t for t in dts_tracks if t["index"] == stream_index), None)
                if dts_track:
                    bit_rate = dts_track["bit_rate"]
                    bit_rate_k = str(int(int(bit_rate) / 1000)) + 'k'
                    ffmpeg_cmd.extend([
                        f"-c:a:{map_count}", "eac3",
                        f"-b:a:{map_count}", bit_rate_k
                    ])
                    map_count += 1
                else:
                    # Pour les autres pistes audio, copier sans modification
                    ffmpeg_cmd.extend([f"-c:a:{map_count}", "copy"])
                    map_count += 1

            elif codec_type == "video":
                # Pour tous les autres flux, copier sans modification
                ffmpeg_cmd.extend([f"-c:v", "copy"])
            
            elif codec_type == "subtitle":
                # Pour les sous-titres, copier sans modification
                ffmpeg_cmd.extend([f"-c:s", "copy"])
        
        # Ajouter les métadonnées et le fichier de sortie
        ffmpeg_cmd.extend(["-map_metadata", "0", "-y", output_file])
        
        # Journaliser la commande pour le débogage
        cmd_str = " ".join(ffmpeg_cmd)
        print(f"Exécution de la commande: {cmd_str}")
        
        # Exécuter la commande ffmpeg - CORRECTION ICI
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,  # Passage de la liste complète sans découpage
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_message = stderr.decode()
            print(f"Erreur ffmpeg: {error_message}")
            conversions[conversion_id]["status"] = f"Échec de la conversion"
            send_telegram_message(f"<b>Conversion échouée</b> pour <code>{file_path}</code>: {error_message}")
        else:
            conversions[conversion_id]["status"] = "Terminé avec succès"
            send_telegram_message(f"<b>Conversion réussie</b> pour <code>{file_path}</code>")
            
            # Remplacer le fichier original par le nouveau
            os.rename(output_file, file_path)
            
        conversions[conversion_id]["end_time"] = datetime.datetime.now()
        
    except Exception as e:
        print(f"Exception lors de la conversion: {str(e)}")
        conversions[conversion_id]["status"] = f"Erreur: {str(e)}"
        conversions[conversion_id]["end_time"] = datetime.datetime.now()
        send_telegram_message(f"<b>Erreur lors de la conversion</b> pour <code>{file_path}</code>: {str(e)}")

async def process_directory(directory_path: str, background_tasks: BackgroundTasks):
    """Traite tous les fichiers dans un répertoire."""
    conversion_ids = []
    
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Créer un ID unique pour cette conversion
            conversion_id = str(uuid.uuid4())
            
            # Enregistrer cette conversion
            conversions[conversion_id] = {
                "id": conversion_id,
                "filename": file_path,
                "start_time": datetime.datetime.now(),
                "end_time": None,
                "status": "En attente"
            }
            
            # Lancer la conversion en arrière-plan
            background_tasks.add_task(convert_dts_to_eac3, file_path, conversion_id)
            conversion_ids.append(conversion_id)
    
    return conversion_ids

def format_time_diff(start, end=None):
    """Formate la différence de temps au format HHh MMmin SSsec."""
    if end is None:
        end = datetime.datetime.now()
        
    diff = end - start
    total_seconds = int(diff.total_seconds())
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"{hours:02d}h {minutes:02d}min {seconds:02d}sec"

@app.post("/convert/", status_code=202)
async def convert_video(video: VideoPath, background_tasks: BackgroundTasks):
    """Endpoint pour lancer la conversion d'un fichier vidéo ou de tous les fichiers d'un répertoire."""
    path = video.path
    
    # Vérifier si le chemin existe
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Chemin non trouvé")
    
    # Si c'est un répertoire, traiter tous les fichiers qu'il contient
    if os.path.isdir(path):
        conversion_ids = await process_directory(path, background_tasks)
        return {
            "message": f"Traitement du répertoire lancé. {len(conversion_ids)} fichiers en cours de traitement.",
            "conversion_ids": conversion_ids
        }
    
    # Si c'est un fichier unique
    else:
        # Créer un ID unique pour cette conversion
        conversion_id = str(uuid.uuid4())
        file_name = os.path.basename(path)
        
        # Enregistrer cette conversion
        conversions[conversion_id] = {
            "id": conversion_id,
            "filename": file_name,
            "start_time": datetime.datetime.now(),
            "end_time": None,
            "status": "En attente"
        }
        
        # Lancer la conversion en arrière-plan
        background_tasks.add_task(convert_dts_to_eac3, path, conversion_id)
        
        return {"id": conversion_id, "message": "Conversion lancée"}

@app.get("/conversions/", response_model=List[ConversionStatus])
async def list_conversions():
    """Liste toutes les conversions avec leur statut."""
    result = []
    
    for conversion_id, info in conversions.items():
        start_time = info["start_time"]
        end_time = info["end_time"]
        
        if end_time:
            elapsed_time = format_time_diff(start_time, end_time)
        else:
            elapsed_time = format_time_diff(start_time)
            
        result.append(
            ConversionStatus(
                id=conversion_id,
                filename=info["filename"],
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S") if end_time else None,
                status=info["status"],
                elapsed_time=elapsed_time
            )
        )
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)