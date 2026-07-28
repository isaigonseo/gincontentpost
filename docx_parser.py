import os
from docx import Document
from unidecode import unidecode
import re
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

def slugify(text):
    """
    Converts text to a slug.
    Example: "Phần mềm SEO" -> "phan-mem-seo"
    """
    text = unidecode(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def iter_block_items(parent):
    """
    Generate a reference to each paragraph and table child within *parent*,
    in document order.
    """
    if parent.__class__.__name__ == 'Document':
        parent_elm = parent.element.body
    elif parent.__class__.__name__ == '_Cell':
        parent_elm = parent._tc
    else:
        raise ValueError("something's not right")
    for child in parent_elm.iterchildren():
        if child.__class__.__name__ == 'CT_P':
            yield Paragraph(child, parent)
        elif child.__class__.__name__ == 'CT_Tbl':
            yield Table(child, parent)

def parse_docx(file_path, image_files, wp_upload_media_func, post_type="posts"):
    """
    Parses docx, uploads matching images via wp_upload_media_func, 
    and returns (title, meta_desc, body_html).
    """
    is_category = (post_type == "categories")
    doc = Document(file_path)
    
    blocks = []
    for item in iter_block_items(doc):
        if isinstance(item, Paragraph):
            if item.text.strip() != '':
                blocks.append(item)
        elif isinstance(item, Table):
            blocks.append(item)
            
    if not blocks:
        raise Exception("File Word không có nội dung.")
        
    meta_desc = ""
    title = ""
    body_blocks = []
    
    # meta_desc is the text of the first block
    if isinstance(blocks[0], Paragraph):
        meta_desc = blocks[0].text.strip()
        
    # title is the text of the first Heading 1
    # body_blocks is everything else (excluding the meta_desc block and the title block)
    title_block = None
    for block in blocks:
        if isinstance(block, Paragraph):
            style_name = block.style.name if block.style else ""
            if style_name == 'Heading 1':
                title = block.text.strip()
                title_block = block
                break
                
    if not title:
        # If no Heading 1 found, fallback to the second block if it exists
        if len(blocks) > 1 and isinstance(blocks[1], Paragraph):
            title = blocks[1].text.strip()
            title_block = blocks[1]
            
    # Filter out the meta_desc block and title block from the body
    for i, block in enumerate(blocks):
        if i == 0:  # Skip meta_desc block
            continue
        if block is title_block:  # Skip title block
            continue
        body_blocks.append(block)
    
    image_map = {}
    for img_path in image_files:
        filename = os.path.basename(img_path)
        name, _ = os.path.splitext(filename)
        image_map[name.lower()] = img_path
        
    html_lines = []
    used_images = set()
    
    in_ul = False
    in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol, html_lines
        if in_ul:
            html_lines.append('</ul>' if is_category else '</ul>\n<!-- /wp:list -->')
            in_ul = False
        if in_ol:
            html_lines.append('</ol>' if is_category else '</ol>\n<!-- /wp:list -->')

    for block in body_blocks:
        if isinstance(block, Table):
            close_lists()
            if is_category:
                html_lines.append('<table border="1">\n<tbody>')
            else:
                html_lines.append('<!-- wp:table -->\n<figure class="wp-block-table"><table>\n<tbody>')
            
            for row in block.rows:
                html_lines.append('<tr>')
                for cell in row.cells:
                    cell_text = cell.text.strip().replace('\n', '<br/>')
                    html_lines.append(f'<td>{cell_text}</td>')
                html_lines.append('</tr>')
                
            if is_category:
                html_lines.append('</tbody>\n</table>')
            else:
                html_lines.append('</tbody>\n</table></figure>\n<!-- /wp:table -->')
            
        elif isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
                
            line_slug = slugify(text)
            
            if line_slug in image_map:
                close_lists()
                used_images.add(line_slug)
                img_file_path = image_map[line_slug]
                alt_text = text # Original Vietnamese text with accents
                
                try:
                    img_res = wp_upload_media_func(img_file_path, alt_text)
                    img_url = img_res['url'] if isinstance(img_res, dict) else img_res
                    media_id = img_res['id'] if isinstance(img_res, dict) else ""
                    
                    if media_id:
                        img_html = f'[caption id="attachment_{media_id}" align="aligncenter" width="800"]<img src="{img_url}" alt="{alt_text}" title="{alt_text}" class="wp-image-{media_id} size-full" /> {alt_text}[/caption]'
                    else:
                        img_html = f'<p style="text-align: center;"><img src="{img_url}" alt="{alt_text}" title="{alt_text}" class="aligncenter" style="margin: 0 auto;" /></p>'
                    
                    html_lines.append(img_html)
                except Exception as e:
                    if is_category:
                        html_lines.append(f'<p style="color:red;">Lỗi upload ảnh {os.path.basename(img_file_path)}: {str(e)}</p>')
                    else:
                        html_lines.append(f'<!-- wp:paragraph -->\n<p style="color:red;">Lỗi upload ảnh {os.path.basename(img_file_path)}: {str(e)}</p>\n<!-- /wp:paragraph -->')
            else:
                p_html = ""
                for run in block.runs:
                    run_text = run.text.replace('<', '&lt;').replace('>', '&gt;')
                    if not run_text:
                        continue
                    if run.bold:
                        run_text = f"<strong>{run_text}</strong>"
                    if run.italic:
                        run_text = f"<em>{run_text}</em>"
                    p_html += run_text
                
                style_name = block.style.name if block.style else ""
                
                is_list = False
                is_ordered = False
                
                if block._p.pPr is not None and block._p.pPr.numPr is not None:
                    is_list = True
                    is_ordered = 'List Number' in style_name
                elif 'List Number' in style_name:
                    is_list = True
                    is_ordered = True
                elif 'List' in style_name:
                    is_list = True
                    is_ordered = False
                
                if is_list:
                    if is_ordered:
                        if in_ul: close_lists()
                        if not in_ol:
                            html_lines.append('<ol>' if is_category else '<!-- wp:list {"ordered":true} -->\n<ol class="wp-block-list">')
                            in_ol = True
                        html_lines.append(f"<li>{p_html}</li>")
                    else:
                        if in_ol: close_lists()
                        if not in_ul:
                            html_lines.append('<ul>' if is_category else '<!-- wp:list -->\n<ul class="wp-block-list">')
                            in_ul = True
                        html_lines.append(f"<li>{p_html}</li>")
                elif style_name.startswith('Heading'):
                    close_lists()
                    try:
                        level = int(style_name.replace('Heading ', ''))
                        if is_category:
                            html_lines.append(f'<h{level} style="text-align: left;">{p_html}</h{level}>')
                        else:
                            html_lines.append(f'<!-- wp:heading {{"level":{level}}} -->\n<h{level} class="wp-block-heading">{p_html}</h{level}>\n<!-- /wp:heading -->')
                    except:
                        if is_category:
                            html_lines.append(f'<p style="text-align: left;">{p_html}</p>')
                        else:
                            html_lines.append(f"<!-- wp:paragraph -->\n<p>{p_html}</p>\n<!-- /wp:paragraph -->")
                else:
                    close_lists()
                    if is_category:
                        html_lines.append(f'<p style="text-align: left;">{p_html}</p>')
                    else:
                        html_lines.append(f"<!-- wp:paragraph -->\n<p>{p_html}</p>\n<!-- /wp:paragraph -->")
                    
    close_lists()
                
    body_html = "\n".join(html_lines)
    
    thumbnail_media_id = None
    unused_images = [img_path for slug, img_path in image_map.items() if slug not in used_images]
    if unused_images:
        thumb_path = unused_images[0]
        try:
            thumb_res = wp_upload_media_func(thumb_path, title)
            thumbnail_media_id = thumb_res['id'] if isinstance(thumb_res, dict) else None
        except Exception as e:
            if is_category:
                html_lines.append(f'<p style="color:red;">Lỗi upload ảnh đại diện: {str(e)}</p>')
            else:
                html_lines.append(f'<!-- wp:paragraph -->\n<p style="color:red;">Lỗi upload ảnh đại diện: {str(e)}</p>\n<!-- /wp:paragraph -->')
    
    return title, meta_desc, body_html, thumbnail_media_id
