import os
from docx import Document
from unidecode import unidecode
import re

def slugify(text):
    """
    Converts text to a slug.
    Example: "Phần mềm SEO" -> "phan-mem-seo"
    """
    text = unidecode(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def parse_docx(file_path, image_files, wp_upload_media_func):
    """
    Parses docx, uploads matching images via wp_upload_media_func, 
    and returns (title, meta_desc, body_html).
    
    wp_upload_media_func is a callback that takes (file_path, alt_text) 
    and returns the uploaded image URL.
    """
    doc = Document(file_path)
    
    paragraphs = [p for p in doc.paragraphs if p.text.strip() != '']
    
    if len(paragraphs) < 2:
        raise Exception("File Word không đủ nội dung (cần ít nhất Meta Description và Tiêu đề).")
        
    meta_desc = paragraphs[0].text.strip()
    title = paragraphs[1].text.strip()
    
    # Process the rest of the body
    body_paragraphs = paragraphs[2:]
    
    # Remove the last image logic:
    # According to requirements: "Trong bài docx chỉ có 1 ảnh duy nhất, bỏ qua ảnh đó là được"
    # Word docx images are embedded in runs. We can just ignore ALL images embedded in the docx.
    # We only care about text.
    
    # Create a mapping from image slug to its actual file path
    image_map = {}
    for img_path in image_files:
        filename = os.path.basename(img_path)
        name, _ = os.path.splitext(filename)
        # Assuming the filename is already slugified (e.g. phan-mem-seo)
        image_map[name.lower()] = img_path
        
    html_lines = []
    
    # To ignore the final check unique text, we could look for a specific keyword or just drop the last paragraph if it's known to be the check unique text.
    # The requirement says: "Ảnh cần đăng nằm cùng thư mục... Cuối bài có hình ảnh check unique thì cần bỏ qua."
    # Since we ignore ALL embedded docx images, the unique check image is automatically ignored.
    # If there is also text for check unique, they didn't explicitly say to remove a specific text, just "bỏ qua ảnh đó là được".
    
    for p in body_paragraphs:
        text = p.text.strip()
        if not text:
            continue
            
        # Check if this line is an alt text placeholder for an image
        line_slug = slugify(text)
        
        if line_slug in image_map:
            # It's an image!
            img_file_path = image_map[line_slug]
            alt_text = text # Original Vietnamese text with accents
            
            # Upload the image and get URL
            # Note: This makes the parsing process blocking and requires network.
            # We could separate it, but doing it inline is straightforward.
            try:
                img_url = wp_upload_media_func(img_file_path, alt_text)
                # Build HTML img tag
                img_html = f'<p><img src="{img_url}" alt="{alt_text}" class="aligncenter" /></p>'
                html_lines.append(img_html)
            except Exception as e:
                # If upload fails, just keep the text or add a comment
                html_lines.append(f'<p style="color:red;">Lỗi upload ảnh {os.path.basename(img_file_path)}: {str(e)}</p>')
        else:
            # It's regular text. Convert basic formatting to HTML.
            # For simplicity, we can just wrap the whole paragraph in <p>
            # To preserve bold/italic, we need to iterate over runs.
            p_html = ""
            for run in p.runs:
                run_text = run.text.replace('<', '&lt;').replace('>', '&gt;')
                if not run_text:
                    continue
                if run.bold:
                    run_text = f"<strong>{run_text}</strong>"
                if run.italic:
                    run_text = f"<em>{run_text}</em>"
                p_html += run_text
            
            if p.style.name.startswith('Heading'):
                # Extract level
                try:
                    level = int(p.style.name.replace('Heading ', ''))
                    html_lines.append(f"<h{level}>{p_html}</h{level}>")
                except:
                    html_lines.append(f"<p>{p_html}</p>")
            else:
                html_lines.append(f"<p>{p_html}</p>")
                
    body_html = "\n".join(html_lines)
    
    return title, meta_desc, body_html
