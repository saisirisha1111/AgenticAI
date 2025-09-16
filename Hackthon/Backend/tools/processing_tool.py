# from google.adk.tools import tool
import os
from dotenv import load_dotenv
from google.cloud import storage, vision,speech
import fitz
from pydub import AudioSegment
from tempfile import NamedTemporaryFile
from pathlib import Path
import logging
from fastapi import HTTPException


load_dotenv()

logger = logging.getLogger(__name__)

storage_client = storage.Client()
vision_client = vision.ImageAnnotatorClient()
 
def process_document(bucket_name: str, file_paths: list[str]) -> dict:
    """
    Extracts text content from PDF documents in GCS using Cloud Vision.
    Args:
        bucket_name: GCS bucket name
        file_paths: List of file paths in the bucket
    Returns:
        dict: { "extracted_documents": [{ "file": str, "content": str }] }
    """
    all_texts = []
 
    for blob_name in file_paths:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
 
        if not blob.exists():
            raise FileNotFoundError(f"{file_path} not found in {bucket_name}")
        if blob_name.lower().endswith(".mp3"):
            # Transcribe audio and append text directly
            extracted_text = transcribe_audio(blob)
            print(f"audio_extracted_text:",{extracted_text})
            # all_texts.append({"file": blob_name, "content": transcript})

        elif blob_name.lower().endswith(".pdf"):
            file_bytes = blob.download_as_bytes()
            extracted_text = extract_text_from_pdf(file_bytes)
            print(f"pdf_extracted:",{extracted_text})
        elif blob_name.lower().endswith(".txt"):
            extracted_text = blob.download_as_text()
        else:
            extracted_text = f"[Unsupported file type: {blob_name}]"
 
        all_texts.append({"file": blob_name, "content": extracted_text})
 
    return {"extracted_documents": all_texts}
 

 
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF file (as bytes) using PyMuPDF + Cloud Vision API.
    Each page is rendered as an image and sent to Vision for OCR.
    """
 
    text = ""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
 
    for page_num, page in enumerate(doc, start=1):
        pix = page.get_pixmap()  # render page to image
        img_bytes = pix.tobytes("png")
 
        image = vision.Image(content=img_bytes)
        response = vision_client.document_text_detection(image=image)
 
        if response.error.message:
            return f"Cloud Vision API error: {response.error.message}"
 
        text += response.full_text_annotation.text + "\n"
 
    return text





def transcribe_audio(blob) -> str:
    """
    Transcribes MP3 audio from a GCS blob and returns text directly.
    """
    speech_client = speech.SpeechClient()

    if not blob.exists():
        logger.error(f"Audio file not found: {blob.name} in {blob.bucket.name}")
        raise HTTPException(status_code=404, detail="MP3 file not found in source bucket.")

    with NamedTemporaryFile(suffix=".mp3") as mp3_file, NamedTemporaryFile(suffix=".wav") as wav_file:
        blob.download_to_filename(mp3_file.name)

        audio = AudioSegment.from_mp3(mp3_file.name)
        audio.export(wav_file.name, format="wav")

        temp_wav_name = f"temp/{Path(wav_file.name).name}"
        temp_blob = blob.bucket.blob(temp_wav_name)
        temp_blob.upload_from_filename(wav_file.name)

        gcs_uri = f"gs://{blob.bucket.name}/{temp_wav_name}"

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=audio.frame_rate,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        recognition_audio = speech.RecognitionAudio(uri=gcs_uri)

        try:
            operation = speech_client.long_running_recognize(config=config, audio=recognition_audio)
            response = operation.result(timeout=600)
        finally:
            temp_blob.delete()

        return " ".join([result.alternatives[0].transcript for result in response.results]).strip()


