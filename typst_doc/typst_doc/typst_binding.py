import frappe, typst, base64, os, json
from datetime import datetime
import resource
import functools
import time


def profile_resources(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        usage_start = resource.getrusage(resource.RUSAGE_SELF)
        start_cpu = time.process_time()
        result = func(*args, **kwargs)
        end_cpu = time.process_time()
        usage_end = resource.getrusage(resource.RUSAGE_SELF)
        cpu_time = end_cpu - start_cpu
        memory_used = usage_end.ru_maxrss - usage_start.ru_maxrss
        print(f"{func.__name__} used {cpu_time:.4f} CPU seconds and {memory_used}KB")
        return result

    return wrapper


@profile_resources
def generate_pdf_with_typst(typ_file_path, pdf_file_path):
    try:
        typst.compile(typ_file_path, output=pdf_file_path)
        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error during PDF compilation: {str(e)}",
            "pdf_file_path": pdf_file_path,
            "typ_file_path": typ_file_path,
        }


@frappe.whitelist()
def build(markup, doctype, docname):
    doc = document_to_json(doctype, docname)
    template_base = f"typst_templates/{doctype}/{doctype}.typ"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # typ_file_name = f"{docname}-{timestamp}.typ"
    typ_file_name = f"typst_templates/{doctype}/{doctype}.typ"
    pdf_file_name = f"{timestamp}.pdf"
    json_file_name = f"typst_templates/{doctype}/data.json"

    files_path = frappe.utils.get_files_path(create_if_not_exists=True)
    typ_file_path = os.path.join(files_path, typ_file_name)
    pdf_file_path = os.path.join(files_path, pdf_file_name)
    json_file_path = os.path.join(files_path, json_file_name)

    # Write the Typst content and JSON data to files
    try:
        with open(json_file_path, "w") as json_file:
            json_file.write(doc)
    except Exception as e:
        return {"status": "error", "message": f"Failed to write files: {str(e)}"}

    # Generate PDF using Typst
    pdf_result = generate_pdf_with_typst(typ_file_path, pdf_file_path)
    if pdf_result["status"] == "error":
        return pdf_result

    return {
        "status": "success",
        "message": "PDF created successfully",
        "pdf_file_path": pdf_file_path,
        "typ_file_path": typ_file_path,
        "doc": doc,
        "json_file_path": json_file_path,
        "template_base": template_base,
    }


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to convert datetime objects to strings."""

    def default(self, obj):
        if isinstance(obj, datetime):
            # Format the datetime object as a string
            return obj.isoformat()
        # For any other types, use the default handling
        return super().default(obj)


def document_to_json(doctype, docname):
    doc = frappe.get_doc(doctype, docname)
    doc_dict = doc.as_dict()

    # Use the custom encoder here if necessary, especially to handle datetime objects
    json_data = json.dumps(doc_dict, indent=4, cls=DateTimeEncoder)

    return json_data
