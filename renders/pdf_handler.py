import fitz
import tempfile
import os

from PIL import Image
from datetime import datetime

from firebase_admin import storage
from firebase_admin import firestore

bucket = storage.bucket()
db = firestore.client()


def create_alarm_bmp(auth_uid, device_id, color_mode):

    doc = (
        db.collection("users")
        .document(auth_uid)
        .collection("devices")
        .document(device_id)
        .collection("modes")
        .document(color_mode)
        .get()
    )

    if not doc.exists:
        return False

    data = doc.to_dict()

    current_pdf = data.get("currentPdf", 0)
    current_page = data.get("currentPage", 0)


    # Find all PDFs automatically

    pdf_prefix = f"users/{auth_uid}/pdfs/"

    pdf_blobs = sorted(
        [
            blob
            for blob in bucket.list_blobs(prefix=pdf_prefix)
            if blob.name.lower().endswith(".pdf")
        ],
        key=lambda x: x.name
    )

    if not pdf_blobs:
        print("No PDF found.")
        return False

    # Safety
    if current_pdf >= len(pdf_blobs):
        current_pdf = 0

    blob = pdf_blobs[current_pdf]

    print(f"Using PDF : {blob.name}")


    # Download PDF

    tmp_pdf = tempfile.NamedTemporaryFile(
        suffix=".pdf",
        delete=False
    )

    tmp_pdf.close()

    blob.download_to_filename(tmp_pdf.name)

    pdf = fitz.open(tmp_pdf.name)

    total_pages = pdf.page_count


    # Next PDF if finished

    if current_page >= total_pages:

        pdf.close()

        current_pdf += 1
        current_page = 0

        if current_pdf >= len(pdf_blobs):
            current_pdf = 0

        doc.reference.update({
            "currentPdf": current_pdf,
            "currentPage": current_page
        })

        os.remove(tmp_pdf.name)

        # Load next PDF
        return create_alarm_bmp(
            auth_uid,
            device_id,
            color_mode
        )


    # Convert page

    page = pdf.load_page(current_page)

    pix = page.get_pixmap(
        dpi=200,
        alpha=False
    )

    img = Image.frombytes(
        "RGB",
        (pix.width, pix.height),
        pix.samples
    )

    img = img.resize(
        (1200, 1600),
        Image.LANCZOS
    )

    tmp_bmp = tempfile.NamedTemporaryFile(
        suffix=".bmp",
        delete=False
    )

    tmp_bmp.close()

    img.save(
        tmp_bmp.name,
        format="BMP"
    )


    # Upload BMP

    today = datetime.now().strftime("%Y%m%d")

    upload_path = (
        f"users/{auth_uid}/devices/{device_id}/"
        f"images/{color_mode}/Frame/alarm1/{today}.bmp"
    )

    bucket.blob(upload_path).upload_from_filename(
        tmp_bmp.name,
        content_type="image/bmp"
    )

    print("Uploaded:", upload_path)


    # Update Firestore

    doc.reference.update({

        "currentPdf": current_pdf,

        "currentPage": current_page + 1,

        "totalPages": total_pages,

        "lastPdf": blob.name,

        "lastUpdated": firestore.SERVER_TIMESTAMP

    })

    pdf.close()

    os.remove(tmp_pdf.name)
    os.remove(tmp_bmp.name)

    return True