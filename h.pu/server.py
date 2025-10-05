# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

def read_links_file():
    """قراءة محتوى ملف links_mon.txt"""
    links_file = 'links_mon.txt'
    
    if not os.path.exists(links_file):
        return {}
    
    users_data = {}
    current_user = None
    
    with open(links_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.endswith(':'):
                current_user = line[:-1]
                users_data[current_user] = []
            elif line and current_user and line != '---':
                users_data[current_user].append(line)
    
    return users_data

def write_links_file(all_users_data):
    """كتابة محتوى ملف links_mon.txt"""
    links_file = 'links_mon.txt'
    
    with open(links_file, 'w', encoding='utf-8') as f:
        for username, links in all_users_data.items():
            f.write(f"{username}:\n")
            for link in links:
                f.write(f"{link}\n")
            f.write("\n")

@app.route('/')
def index():
    return send_file('tiktok_monitor.html')

@app.route('/delete_videos', methods=['POST'])
def delete_videos():
    """حذف فيديوهات من الملف"""
    try:
        data = request.json
        urls_to_delete = data.get('urls', [])
        
        all_users_data = read_links_file()
        
        for username, links in all_users_data.items():
            all_users_data[username] = [link for link in links if link not in urls_to_delete]
        
        write_links_file(all_users_data)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_hidden', methods=['POST'])
def save_hidden():
    """حفظ قائمة الفيديوهات المخفية"""
    try:
        data = request.json
        hidden_list = data.get('hidden', [])
        
        with open('hidden_videos.json', 'w', encoding='utf-8') as f:
            json.dump(hidden_list, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
