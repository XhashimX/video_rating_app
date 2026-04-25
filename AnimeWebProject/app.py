import json
import math
import requests # تأكد من تثبيتها عبر pip install requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATA_FILE = "anime-offline-database-minified.json"
anime_database = []
available_years = []
top_tags = []

def load_data():
    global anime_database, available_years, top_tags
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            anime_database = data.get('data', [])
        
        years = {anime['animeSeason']['year'] for anime in anime_database if anime.get('animeSeason') and anime['animeSeason'].get('year')}
        available_years = sorted(list(years), reverse=True)
        
        tag_counts = {}
        for anime in anime_database:
            for tag in anime.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = [tag for tag, count in sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:30]]

        print(f"Loaded {len(anime_database)} anime successfully!")
    except Exception as e:
        print(f"Error loading database: {e}")

load_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/meta')
def get_meta_data():
    return jsonify({"years": available_years, "tags": top_tags, "total_anime": len(anime_database)})

@app.route('/api/anime')
def get_anime():
    query = request.args.get('q', '').lower()
    anime_type = request.args.get('type', '')
    year = request.args.get('year', '')
    season = request.args.get('season', '')
    status = request.args.get('status', '')
    has_score = request.args.get('has_score', 'false').lower() == 'true'
    tag = request.args.get('tag', '')
    sort_by = request.args.get('sort', 'yr-d')
    page = int(request.args.get('page', 1))
    per_page = 48

    results = []
    for anime in anime_database:
        if query and not (query in anime.get('title', '').lower() or any(query in s.lower() for s in anime.get('synonyms', []))): continue
        if anime_type and anime.get('type') != anime_type: continue
        if year and (not anime.get('animeSeason') or str(anime.get('animeSeason', {}).get('year')) != year): continue
        if season and (not anime.get('animeSeason') or anime.get('animeSeason', {}).get('season') != season): continue
        if status and anime.get('status') != status: continue
        if has_score and not anime.get('score'): continue
        if tag and tag not in anime.get('tags', []): continue
        results.append(anime)

    if sort_by == 'ti-a': results.sort(key=lambda x: x.get('title', ''))
    elif sort_by == 'ti-d': results.sort(key=lambda x: x.get('title', ''), reverse=True)
    elif sort_by == 'yr-a': results.sort(key=lambda x: x.get('animeSeason', {}).get('year') or 0)
    elif sort_by == 'yr-d': results.sort(key=lambda x: x.get('animeSeason', {}).get('year') or 0, reverse=True)
    elif sort_by == 'sc-a': results.sort(key=lambda x: x.get('score', {}).get('arithmeticMean') or 11)
    elif sort_by == 'sc-d': results.sort(key=lambda x: x.get('score', {}).get('arithmeticMean') or 0, reverse=True)
    elif sort_by == 'ep-d': results.sort(key=lambda x: x.get('episodes') or 0, reverse=True)
    
    total_items = len(results)
    total_pages = math.ceil(total_items / per_page)
    paginated_results = results[(page - 1) * per_page:page * per_page]

    return jsonify({"data": paginated_results, "page": page, "total_pages": total_pages, "total_items": total_items})

# مسار جديد لجلب الشخصيات من Jikan API
@app.route('/api/characters/<int:mal_id>')
def get_characters(mal_id):
    try:
        url = f"https://api.jikan.moe/v4/anime/{mal_id}/characters"
        response = requests.get(url, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# مسار جديد لجلب تفاصيل الشخصية (Bio)
@app.route('/api/character-info/<int:char_id>')
def get_char_info(char_id):
    try:
        url = f"https://api.jikan.moe/v4/characters/{char_id}"
        response = requests.get(url, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)