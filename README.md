# BoringChatBot
无聊机器人


## 使用 Alembic 生成数据表
1. pip install alembic psycopg2-binary sqlalchemy
2. 关联数据表db_model.py 和 alembic.ini 和 alembic、alembic/env.py
3. 使用 pgAdmin 工具创建 boring_chatbot 数据表
4. alembic init alembic
5. 生成迁移文件 
    
   alembic revision --autogenerate -m "create files table"
6. 应用迁移 
 
   alembic upgrade head