import sys
import base64   # required for decoding email body/attachments



print("Starting script...")  # Ensure the script is running

try:
    import pickle
    import os
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    # Define the scopes for Gmail API
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://mail.google.com/',
        'https://www.googleapis.com/auth/drive.metadata.readonly',  
        'https://www.googleapis.com/auth/drive.readonly',
    ]

    def get_gmail_service():
        """Gets authenticated Gmail service."""
        print("Inside get_gmail_service function...")
        creds = None
        token_path = r'/workspace/AgenticAI/Hackthon/Backend/token.pickle'
        if os.path.exists(token_path):
            print("Token file exists. Loading credentials...")
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        else:
            print("No token file available.")

        # If there are no valid credentials, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("Fetching new credentials from client secret file...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    r'/workspace/AgenticAI/Hackthon/Backend/credentials.json', SCOPES
                )
                # try:
                #     print("in local server")
                #     # First try local server flow (works on local machines)
                #     creds = flow.run_local_server(port=8080)
                # except Exception:
                #     # Fallback for cloud/server environments
                print("⚠️ Local server auth failed, switching to console auth...")
                creds = flow.run_console()
            
            # Save the credentials for the next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
                print("New token saved successfully.")

        return build('gmail', 'v1', credentials=creds)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)




def check_email_inbox(sender_email: str) -> dict:
    """
    Fetch emails from a specific sender. 
    Return body + attachments (only if >25MB).
    """
    try:
        service = get_gmail_service()
        query = sender_email

        results = service.users().messages().list(
            userId='me', q=query, maxResults=10
        ).execute()
        messages = results.get('messages', [])

        if not messages:
            return {"status": f"No new emails found from {sender_email}."}

        email_data_list = []

        for message in messages:
            msg = service.users().messages().get(
                userId='me', id=message['id'], format='full'
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            snippet = msg.get("snippet", "")

            # --- Extract body text ---
            body_text = ""
            payload = msg.get("payload", {})
            parts = payload.get("parts", [])
            if not parts:  # Simple email without attachments
                body_data = payload.get("body", {}).get("data")
                if body_data:
                    body_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
            else:
                for part in parts:
                    if part.get("mimeType") == "text/plain":
                        body_data = part.get("body", {}).get("data")
                        if body_data:
                            body_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

            attachments_data = []
            for part in parts:
                if part.get("filename"):
                    attach_id = part.get("body", {}).get("attachmentId")
                    attach_size = int(part.get("body", {}).get("size", 0))

                    if attach_id and attach_size > 25 * 1024 * 1024:  # Only fetch if >25MB
                        attachments_data.append({
                            "filename": part["filename"],
                            "size": attach_size,
                            "data": "file size is more then 25MB"  # raw binary data
                        })

                    else:
                        attachment = service.users().messages().attachments().get(
                            userId="me", messageId=message['id'], id=attach_id
                        ).execute()

                        file_data = base64.urlsafe_b64decode(attachment.get("data"))
                        attachments_data.append({
                            "filename": part["filename"],
                            "size": attach_size,
                            "data": file_data  # raw binary data
                        })

            email_data_list.append({
                "subject": subject,
                "from": sender,
                "snippet": snippet,
                "body": body_text,
                "attachments_over_25mb": attachments_data
            })
            print(f"email_data_list:{email_data_list}")

        return {"status": "success", "emails": email_data_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}
