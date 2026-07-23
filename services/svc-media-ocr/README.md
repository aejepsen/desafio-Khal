# Mini-serviço OCR — Tesseract CPU (~0.5–1 GB RAM).
#
# Contrato POST /v1/ocr:
#   {"url": "http://..."} 
#   {"image_base64": "...", "filename": "cnh.png"}
# → {"text": "..."}
#
# No /chat do agente: message_type=image|document + media_url OU media_base64.
