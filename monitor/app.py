#!/usr/bin/env python3
"""
Build Monitor Server - 构建监控服务
部署在 x64 服务器上，接收来自 RISC-V 构建机器的状态上报
"""
import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response

app = Flask(__name__, static_folder='static', static_url_path='')

# 配置
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'builds.db'
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine TEXT NOT NULL,
            package TEXT NOT NULL,
            script TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            start_time TEXT NOT NULL,
            end_time TEXT,
            log_file TEXT,
            python_version TEXT
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_machine ON builds(machine)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON builds(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_start_time ON builds(start_time DESC)')
    conn.commit()
    conn.close()


# ==================== API 路由 ====================

@app.route('/')
def index():
    """返回监控仪表盘页面"""
    return send_from_directory('static', 'index.html')


@app.route('/api/build/start', methods=['POST'])
def build_start():
    """上报构建开始"""
    data = request.json
    machine = data.get('machine', 'unknown')
    package = data.get('package', 'unknown')
    script = data.get('script', '')
    python_version = data.get('python_version', '')
    
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO builds (machine, package, script, status, start_time, python_version)
        VALUES (?, ?, ?, 'running', ?, ?)
    ''', (machine, package, script, datetime.now().isoformat(), python_version))
    build_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': build_id, 'status': 'ok'})


@app.route('/api/build/finish', methods=['POST'])
def build_finish():
    """上报构建完成"""
    data = request.json
    build_id = data.get('id')
    status = data.get('status', 'success')  # success / failed
    
    conn = get_db()
    conn.execute('''
        UPDATE builds SET status = ?, end_time = ? WHERE id = ?
    ''', (status, datetime.now().isoformat(), build_id))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok'})


@app.route('/api/build/log', methods=['POST'])
def upload_log():
    """上传构建日志"""
    build_id = request.form.get('id')
    log_file = request.files.get('log')
    
    if not build_id or not log_file:
        return jsonify({'error': 'Missing id or log file'}), 400
    
    # 保存日志文件
    filename = f'build_{build_id}.log'
    log_path = LOGS_DIR / filename
    log_file.save(str(log_path))
    
    # 更新数据库
    conn = get_db()
    conn.execute('UPDATE builds SET log_file = ? WHERE id = ?', (filename, build_id))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok', 'log_file': filename})


@app.route('/api/builds', methods=['GET'])
def list_builds():
    """获取构建列表"""
    limit = request.args.get('limit', 100, type=int)
    machine = request.args.get('machine', '')
    status = request.args.get('status', '')
    
    conn = get_db()
    query = 'SELECT * FROM builds WHERE 1=1'
    params = []
    
    if machine:
        query += ' AND machine = ?'
        params.append(machine)
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    query += ' ORDER BY start_time DESC LIMIT ?'
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    builds = [dict(row) for row in rows]
    conn.close()
    
    return jsonify(builds)


@app.route('/api/build/<int:build_id>/log', methods=['GET'])
def get_log(build_id):
    """获取构建日志内容"""
    conn = get_db()
    row = conn.execute('SELECT log_file FROM builds WHERE id = ?', (build_id,)).fetchone()
    conn.close()
    
    if not row or not row['log_file']:
        return jsonify({'error': 'Log not found'}), 404
    
    log_path = LOGS_DIR / row['log_file']
    if not log_path.exists():
        return jsonify({'error': 'Log file missing'}), 404
    
    content = log_path.read_text(errors='replace')
    return Response(content, mimetype='text/plain; charset=utf-8')


@app.route('/api/machines', methods=['GET'])
def list_machines():
    """获取所有机器列表"""
    conn = get_db()
    rows = conn.execute('SELECT DISTINCT machine FROM builds ORDER BY machine').fetchall()
    machines = [row['machine'] for row in rows]
    conn.close()
    return jsonify(machines)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    conn = get_db()
    
    # 总计
    total = conn.execute('SELECT COUNT(*) as c FROM builds').fetchone()['c']
    running = conn.execute("SELECT COUNT(*) as c FROM builds WHERE status='running'").fetchone()['c']
    success = conn.execute("SELECT COUNT(*) as c FROM builds WHERE status='success'").fetchone()['c']
    failed = conn.execute("SELECT COUNT(*) as c FROM builds WHERE status='failed'").fetchone()['c']
    
    conn.close()
    
    return jsonify({
        'total': total,
        'running': running,
        'success': success,
        'failed': failed
    })


if __name__ == '__main__':
    init_db()
    print("🚀 Build Monitor Server starting...")
    print("📊 Dashboard: http://<server-ip>:5050")
    print("   - Listening on 0.0.0.0:5050 (all interfaces)")
    app.run(host='0.0.0.0', port=5050, debug=False)
