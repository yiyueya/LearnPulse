# 知识图谱Agent - 使用SQLite存储，支持层次结构
from src.services.knowledge_graph_sqlite import SQLiteKnowledgeGraph
from src.utils.logger import logger
import json
from pathlib import Path
from config.config import JSON_DIR

class KnowledgeGraphAgent:
    """知识图谱Agent，负责构建和维护知识地图"""

    def __init__(self):
        self.kg = SQLiteKnowledgeGraph()
        self.json_dir = JSON_DIR

    def _generate_node_id(self, subject, grade, unit, index):
        """生成节点ID: math_g1_u3_p2"""
        grade_map = {'一年级': 'g1', '二年级': 'g2', '三年级': 'g3',
                     '四年级': 'g4', '五年级': 'g5', '六年级': 'g6'}
        grade_code = grade_map.get(grade, 'g1')

        # 处理单元名称
        unit_clean = str(unit).replace('单元', '').strip() if unit else 'u0'
        unit_code = f"u{unit_clean}" if unit_clean.isdigit() else f"u{unit_clean}"

        return f"{subject[:2]}_{grade_code}_{unit_code}_p{index}"

    def _extract_knowledge_items(self, data, subject):
        """递归从JSON数据中提取所有知识点项，保持层次结构"""
        items = []
        if isinstance(data, list):
            for item in data:
                items.extend(self._extract_knowledge_items(item, subject))
        elif isinstance(data, dict):
            # 检查是否是知识点节点
            has_name = bool(data.get("name") or data.get("标题") or data.get("知识点名称"))
            has_content = bool(data.get("content") or data.get("知识点") or data.get("内容"))

            if has_name and has_content:
                name = (data.get("标题") or data.get("name") or
                        data.get("知识点名称") or
                        str(data.get("单元", "")) + "_" + str(data.get("序号", "")))

                knowledge_list = data.get("知识点", [])
                if isinstance(knowledge_list, list) and knowledge_list:
                    content = "; ".join(str(k) for k in knowledge_list[:3])
                else:
                    content = data.get("content") or data.get("内容") or ""

                grade = data.get("grade") or data.get("年级") or "一年级"
                unit = data.get("单元") or data.get("unit") or ""

                items.append({
                    "name": name,
                    "content": content,
                    "grade": grade,
                    "unit": unit,
                    "difficulty": data.get("difficulty", 3),
                    "importance": data.get("importance", 3)
                })

            # 递归处理子节点
            for value in data.values():
                if isinstance(value, (dict, list)):
                    items.extend(self._extract_knowledge_items(value, subject))

        return items

    def _build_prerequisite_chain(self, subject, grade, unit_items):
        """构建单元内的前置关系链（同单元内按顺序）"""
        if len(unit_items) <= 1:
            return

        # 同单元内，按顺序建立前置关系
        for i in range(len(unit_items) - 1):
            source_id = unit_items[i]['node_id']
            target_id = unit_items[i + 1]['node_id']
            self.kg.add_relation(source_id, target_id, '前置', 1.0)

    def _build_cross_grade_relations(self, subject):
        """构建跨年级的前置关系"""
        conn = self.kg._get_conn()
        cursor = conn.cursor()

        # 获取年级顺序
        grade_order = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级']

        for i in range(len(grade_order) - 1):
            current_grade = grade_order[i]
            next_grade = grade_order[i + 1]

            # 获取相邻年级同单元的知识点
            cursor.execute('''
                SELECT k1.id as current_id, k2.id as next_id, k1.unit
                FROM knowledge_points k1
                JOIN knowledge_points k2 ON k1.unit = k2.unit AND k2.grade = ?
                WHERE k1.subject = ? AND k1.grade = ?
            ''', (next_grade, subject, current_grade))

            for row in cursor.fetchall():
                self.kg.add_relation(row['current_id'], row['next_id'], '递进', 0.8)

    def _build_unit_hierarchy(self, subject):
        """构建单元层次结构（包含关系）"""
        conn = self.kg._get_conn()
        cursor = conn.cursor()

        # 获取该学科所有年级
        cursor.execute('''
            SELECT DISTINCT grade FROM knowledge_points
            WHERE subject=? ORDER BY grade
        ''', (subject,))
        grades = [row['grade'] for row in cursor.fetchall()]

        for grade in grades:
            # 获取该年级所有单元
            cursor.execute('''
                SELECT DISTINCT unit FROM knowledge_points
                WHERE subject=? AND grade=? AND unit IS NOT NULL
            ''', (subject, grade))
            units = [row['unit'] for row in cursor.fetchall() if row['unit']]

            for unit in units:
                # 获取单元内所有知识点
                cursor.execute('''
                    SELECT id FROM knowledge_points
                    WHERE subject=? AND grade=? AND unit=?
                ''', (subject, grade, unit))
                points = [row['id'] for row in cursor.fetchall()]

                # 同一单元内建立全连接（知识点少，足够快）
                for i, source_id in enumerate(points):
                    for j, target_id in enumerate(points):
                        if i != j:
                            self.kg.add_relation(source_id, target_id, '关联', 0.5)

    def build_knowledge_map(self, subject):
        """构建指定学科的知识地图"""
        # 清空该学科现有数据
        conn = self.kg._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM relations WHERE source_id IN (SELECT id FROM knowledge_points WHERE subject=?)',
                       (subject,))
        cursor.execute('DELETE FROM knowledge_points WHERE subject=?', (subject,))
        conn.commit()

        # 加载该学科的所有知识点JSON文件
        subject_files = []
        for file in self.json_dir.iterdir():
            if subject in file.name and file.suffix == ".json":
                subject_files.append(file)

        if not subject_files:
            logger.warning(f"未找到{subject}学科的知识点文件")
            return {"status": "warning", "message": f"未找到{subject}学科的知识点文件"}

        # 收集所有知识点
        all_items = []
        for file in subject_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = self._extract_knowledge_items(data, subject)
                    all_items.extend(items)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"读取文件失败 {file}: {e}")
                continue

        if not all_items:
            logger.warning(f"未能从{subject}提取任何知识点")
            return {"status": "warning", "message": "未能提取知识点"}

        # 去重并添加节点
        seen_names = set()
        items_by_grade_unit = {}

        for item in all_items:
            name = item.get("name", "")
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            grade = item.get("grade", "一年级")
            unit = item.get("unit", "")
            key = (grade, unit)

            if key not in items_by_grade_unit:
                items_by_grade_unit[key] = []
            items_by_grade_unit[key].append(item)

        # 添加节点
        node_id_counter = 0
        for (grade, unit), items in items_by_grade_unit.items():
            for i, item in enumerate(items):
                node_id = self._generate_node_id(subject, grade, unit, i)
                item['node_id'] = node_id

                self.kg.add_knowledge_point(
                    node_id=node_id,
                    name=item['name'],
                    subject=subject,
                    grade=grade,
                    unit=unit,
                    difficulty=item.get('difficulty', 3),
                    importance=item.get('importance', 3),
                    content=item.get('content', '')
                )
                node_id_counter += 1

        # 构建单元内前置关系
        for (grade, unit), items in items_by_grade_unit.items():
            if items:
                self._build_prerequisite_chain(subject, grade, items)

        # 构建跨年级关系
        self._build_cross_grade_relations(subject)

        # 构建单元层次结构
        self._build_unit_hierarchy(subject)

        stats = self.kg.get_statistics()
        logger.info(f"{subject}知识地图构建完成: {stats['node_count']}节点, {stats['edge_count']}边")

        return {"status": "success", "message": f"{subject}知识地图构建完成"}

    def build_all_knowledge_maps(self):
        """构建所有学科的知识地图"""
        logger.info("[KnowledgeGraphAgent] Building all knowledge maps")
        subjects = ["数学", "语文"]
        results = {}

        for subject in subjects:
            result = self.build_knowledge_map(subject)
            results[subject] = result

        return results

    def get_knowledge_map_data(self, subject, grade=None, unit=None):
        """获取知识图谱数据（用于前端可视化）"""
        nodes = self.kg.get_knowledge_points(subject=subject, grade=grade, unit=unit)
        relations = self.kg.get_relations()

        # 构建vis-network格式
        nodes_data = []
        for node in nodes:
            nodes_data.append({
                'id': node['id'],
                'label': node['name'],
                'subject': node['subject'],
                'grade': node['grade'],
                'unit': node.get('unit', ''),
                'difficulty': node.get('difficulty', 3),
                'content': node.get('content', '')
            })

        edges_data = []
        node_ids = {n['id'] for n in nodes_data}
        for rel in relations:
            if rel['source_id'] in node_ids and rel['target_id'] in node_ids:
                edges_data.append({
                    'from': rel['source_id'],
                    'to': rel['target_id'],
                    'label': rel['relation_type']
                })

        return {'nodes': nodes_data, 'edges': edges_data}

    def get_learning_path(self, node_id):
        """获取指定节点的学习路径"""
        path_ids = self.kg.get_learning_path(node_id)
        path_nodes = []
        for nid in path_ids:
            node = self.kg.get_node(nid)
            if node:
                path_nodes.append(node)

        # 加上当前节点
        current = self.kg.get_node(node_id)
        if current:
            path_nodes.append(current)

        return path_nodes

    def get_next_learning(self, node_id):
        """获取后续学习节点"""
        return self.kg.get_next_learning(node_id)

    def get_weak_points_related(self, weak_point_ids):
        """获取薄弱点关联的练习推荐"""
        return self.kg.get_weak_points_related(weak_point_ids)