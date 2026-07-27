import requests
import os

def get_categories(url, username, password):
    api_url = f"{url.rstrip('/')}/wp-json/wp/v2/categories"
    response = requests.get(api_url, auth=(username, password), params={'per_page': 100})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Lỗi lấy danh mục: {response.status_code} - {response.text}")

def upload_media(url, username, password, file_path, alt_text):
    api_url = f"{url.rstrip('/')}/wp-json/wp/v2/media"
    
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        file_data = f.read()

    headers = {
        'Content-Disposition': f'attachment; filename="{file_name}"',
        'Content-Type': 'image/jpeg' # Simplification, WordPress will detect actual type
    }

    if file_name.lower().endswith('.png'):
        headers['Content-Type'] = 'image/png'
    elif file_name.lower().endswith('.webp'):
        headers['Content-Type'] = 'image/webp'

    response = requests.post(
        api_url,
        headers=headers,
        data=file_data,
        auth=(username, password)
    )

    if response.status_code == 201:
        media_info = response.json()
        media_id = media_info['id']
        source_url = media_info['source_url']
        
        # Update alt text
        update_url = f"{api_url}/{media_id}"
        update_data = {
            'alt_text': alt_text
        }
        requests.post(update_url, json=update_data, auth=(username, password))
        
        return {
            'id': media_id,
            'url': source_url,
            'alt_text': alt_text
        }
    else:
        raise Exception(f"Lỗi upload ảnh {file_name}: {response.status_code} - {response.text}")

def create_post(url, username, password, title, body, category_id, meta_desc):
    api_url = f"{url.rstrip('/')}/wp-json/wp/v2/posts"
    
    data = {
        'title': title,
        'content': body,
        'status': 'draft', # Create as draft for safety
        'categories': [category_id] if category_id else [],
        'meta': {
            '_yoast_wpseo_metadesc': meta_desc,
            'rank_math_description': meta_desc
        }
    }

    response = requests.post(api_url, json=data, auth=(username, password))
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Lỗi tạo bài viết: {response.status_code} - {response.text}")
