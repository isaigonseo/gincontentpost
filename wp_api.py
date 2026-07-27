import requests
import os
import base64

def get_auth_headers(username, password):
    auth_string = f"{username}:{password}"
    encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    return {
        'Authorization': f'Basic {encoded_auth}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

def get_categories(url, username, password):
    api_url = f"{url.rstrip('/')}/wp-json/wp/v2/categories"
    headers = get_auth_headers(username, password)
    response = requests.get(api_url, headers=headers, params={'per_page': 100})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Lỗi lấy danh mục: {response.status_code} - {response.text}")

def upload_media(url, username, password, file_path, alt_text):
    api_url = f"{url.rstrip('/')}/wp-json/wp/v2/media"
    
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        file_data = f.read()

    headers = get_auth_headers(username, password)
    headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
    headers['Content-Type'] = 'image/jpeg' # Simplification, WordPress will detect actual type

    if file_name.lower().endswith('.png'):
        headers['Content-Type'] = 'image/png'
    elif file_name.lower().endswith('.webp'):
        headers['Content-Type'] = 'image/webp'

    response = requests.post(
        api_url,
        headers=headers,
        data=file_data
    )

    if response.status_code == 201:
        media_info = response.json()
        media_id = media_info['id']
        source_url = media_info['source_url']
        
        # Update alt text
        update_url = f"{api_url}/{media_id}"
        update_headers = get_auth_headers(username, password)
        update_data = {
            'title': {'raw': alt_text},
            'alt_text': alt_text,
            'description': {'raw': alt_text},
            'caption': {'raw': alt_text}
        }
        update_res = requests.post(update_url, json=update_data, headers=update_headers)
        if update_res.status_code >= 400:
            print(f"Warning updating media meta: {update_res.text}")
        
        return {
            'id': media_id,
            'url': source_url,
            'alt_text': alt_text
        }
    else:
        raise Exception(f"Lỗi upload ảnh {file_name}: {response.status_code} - {response.text}")

def create_post(url, username, password, title, body, category_id, meta_desc, slug, post_type="posts", featured_media=None):
    if post_type == "pages":
        api_url = f"{url.rstrip('/')}/wp-json/wp/v2/pages"
        data = {
            'title': title,
            'content': body,
            'status': 'draft', # Create as draft for safety
            'slug': slug,
            'meta': {
                '_yoast_wpseo_metadesc': meta_desc,
                'rank_math_description': meta_desc
            }
        }
        if featured_media:
            data['featured_media'] = featured_media
    elif post_type == "categories":
        api_url = f"{url.rstrip('/')}/wp-json/wp/v2/categories"
        data = {
            'name': title,
            'description': body,
            'slug': slug,
            'meta': {
                'wpseo_desc': meta_desc # Note: category Yoast meta uses wpseo_desc, but we'll try rank_math too if needed
            }
        }
    else: # posts
        api_url = f"{url.rstrip('/')}/wp-json/wp/v2/posts"
        data = {
            'title': title,
            'content': body,
            'status': 'draft', # Create as draft for safety
            'categories': [category_id] if category_id else [],
            'slug': slug,
            'meta': {
                '_yoast_wpseo_metadesc': meta_desc,
                'rank_math_description': meta_desc
            }
        }
        if featured_media:
            data['featured_media'] = featured_media

    headers = get_auth_headers(username, password)
    headers['Content-Type'] = 'application/json'

    # Send without auth=(username, password) tuple so requests doesn't override our headers or drop them
    response = requests.post(api_url, json=data, headers=headers)
    
    # Debug info if 401 happens
    if response.status_code == 401:
        raise Exception(f"401 Unauthorized: Bị chặn bởi tường lửa (WAF/Cloudflare) hoặc mất Authorization header.\nServer Response: {response.text}")
        
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Lỗi tạo bài viết: {response.status_code} - {response.text}")
