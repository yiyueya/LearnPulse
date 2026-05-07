# SQLite知识图谱服务 - 支持层次结构和前置关系
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from config.config import KNOWLEDGE_MAP_DIR

class SQLiteKnowledgeGraph:
    """基于SQLite的知识图谱，支持层次结构和前置关系"""

    def __init__(self, db_path="data/knowledge_graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._init_db()

    def _get_conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 知识点节点表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_points (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade TEXT NOT NULL,
                unit TEXT,
                difficulty INTEGER DEFAULT 3,
                importance INTEGER DEFAULT 3,
                mastery REAL DEFAULT 0.0,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 知识点关系表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY (source_id) REFERENCES knowledge_points(id),
                FOREIGN KEY (target_id) REFERENCES knowledge_points(id)
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subject_grade ON knowledge_points(subject, grade)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id)')

        conn.commit()

    def clear_all(self):
        """清空所有数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM relations')
        cursor.execute('DELETE FROM knowledge_points')
        conn.commit()

    def add_knowledge_point(self, node_id, name, subject, grade, unit=None,
                            difficulty=3, importance=3, mastery=0.0, content=""):
        """添加知识点"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_points
            (id, name, subject, grade, unit, difficulty, importance, mastery, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (node_id, name, subject, grade, unit, difficulty, importance, mastery, content))
        conn.commit()

    def add_relation(self, source_id, target_id, relation_type, weight=1.0):
        """添加知识点关系"""
        conn = self._get_conn()
        cursor = conn.cursor()
        # 检查是否已存在
        cursor.execute('''
            SELECT id FROM relations WHERE source_id=? AND target_id=? AND relation_type=?
        ''', (source_id, target_id, relation_type))
        if cursor.fetchone():
            return  # 已存在，不重复添加

        cursor.execute('''
            INSERT INTO relations (source_id, target_id, relation_type, weight)
            VALUES (?, ?, ?, ?)
        ''', (source_id, target_id, relation_type, weight))
        conn.commit()

    def get_knowledge_points(self, subject=None, grade=None, unit=None):
        """获取知识点列表，支持过滤"""
        conn = self._get_conn()
        cursor = conn.cursor()

        query = 'SELECT * FROM knowledge_points WHERE 1=1'
        params = []

        if subject:
            query += ' AND subject=?'
            params.append(subject)
        if grade:
            query += ' AND grade=?'
            params.append(grade)
        if unit:
            query += ' AND unit=?'
            params.append(unit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_node(self, node_id):
        """获取单个知识点"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM knowledge_points WHERE id=?', (node_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_relations(self, node_id=None, relation_type=None):
        """获取关系列表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        query = 'SELECT * FROM relations WHERE 1=1'
        params = []

        if node_id:
            query += ' AND (source_id=? OR target_id=?)'
            params.extend([node_id, node_id])
        if relation_type:
            query += ' AND relation_type=?'
            params.append(relation_type)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_related_nodes(self, node_id, relation_type=None):
        """获取节点的所有关联节点"""
        conn = self._get_conn()
        cursor = conn.cursor()

        if relation_type:
            cursor.execute('''
                SELECT k.*, r.relation_type, r.weight
                FROM knowledge_points k
                JOIN relations r ON (
                    (r.source_id=? AND r.target_id=k.id) OR
                    (r.target_id=? AND r.source_id=k.id)
                )
                WHERE r.relation_type=? AND k.id != ?
            ''', (node_id, node_id, relation_type, node_id))
        else:
            cursor.execute('''
                SELECT k.*, r.relation_type, r.weight
                FROM knowledge_points k
                JOIN relations r ON (
                    (r.source_id=? AND r.target_id=k.id) OR
                    (r.target_id=? AND r.source_id=k.id)
                )
                WHERE k.id != ?
            ''', (node_id, node_id, node_id))

        return [dict(row) for row in cursor.fetchall()]

    def get_learning_path(self, node_id):
        """获取学习路径（从起点到该节点的前置链）"""
        conn = self._get_conn()
        cursor = conn.cursor()

        path = []
        current_id = node_id

        # 向前追溯前置关系
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            cursor.execute('''
                SELECT source_id FROM relations
                WHERE target_id=? AND relation_type='前置'
            ''', (current_id,))
            row = cursor.fetchone()
            if row:
                current_id = row['source_id']
                path.insert(0, current_id)
            else:
                break

        return path

    def get_next_learning(self, node_id):
        """获取后续学习节点（该节点的后继）"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT k.*, r.weight
            FROM knowledge_points k
            JOIN relations r ON r.target_id=k.id
            WHERE r.source_id=? AND r.relation_type='前置'
        ''', (node_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_weak_points_related(self, weak_point_ids):
        """获取薄弱点关联的练习推荐"""
        conn = self._get_conn()
        cursor = conn.cursor()

        if not weak_point_ids:
            return []

        # 获取所有与薄弱点相关的知识点
        placeholders = ','.join('?' * len(weak_point_ids))
        cursor.execute(f'''
            SELECT DISTINCT k.*
            FROM knowledge_points k
            JOIN relations r ON (
                (r.source_id IN ({placeholders}) AND r.target_id = k.id) OR
                (r.target_id IN ({placeholders}) AND r.source_id = k.id)
            )
            WHERE k.id NOT IN ({placeholders})
            AND r.relation_type IN ('前置', '递进', '关联')
        ''', weak_point_ids + weak_point_ids)

        return [dict(row) for row in cursor.fetchall()]

    def get_unit_hierarchy(self, subject, grade):
        """获取指定学科和年级的单元层次结构"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT unit FROM knowledge_points
            WHERE subject=? AND grade=?
            ORDER BY unit
        ''', (subject, grade))

        units = [row['unit'] for row in cursor.fetchall() if row['unit']]
        return units

    def get_statistics(self):
        """获取图谱统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM knowledge_points')
        node_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM relations')
        edge_count = cursor.fetchone()['count']

        cursor.execute('SELECT subject, grade, COUNT(*) as count FROM knowledge_points GROUP BY subject, grade')
        by_subject_grade = [dict(row) for row in cursor.fetchall()]

        return {
            'node_count': node_count,
            'edge_count': edge_count,
            'by_subject_grade': by_subject_grade
        }

    def export_to_json(self, subject=None):
        """导出为JSON格式（兼容前端vis-network）"""
        nodes_data = self.get_knowledge_points(subject=subject)
        relations_data = self.get_relations()

        # 构建nodes
        nodes = []
        for node in nodes_data:
            nodes.append({
                'id': node['id'],
                'label': node['name'],
                'subject': node['subject'],
                'grade': node['grade'],
                'unit': node.get('unit', ''),
                'difficulty': node.get('difficulty', 3),
                'content': node.get('content', '')
            })

        # 构建edges
        edges = []
        for rel in relations_data:
            # 检查source和target是否在要导出的nodes中
            node_ids = {n['id'] for n in nodes}
            if rel['source_id'] in node_ids and rel['target_id'] in node_ids:
                edges.append({
                    'from': rel['source_id'],
                    'to': rel['target_id'],
                    'label': rel['relation_type']
                })

        return {'nodes': nodes, 'edges': edges}

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None