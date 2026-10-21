import os
from enum import Enum
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from atlassian_loaders import ConfluenceLoader, JiraLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Enum กำหนดค่าสำหรับ Jira
class JiraProject(str, Enum):
    RKB2 = "RKB2"


class JiraStatus(str, Enum):
    DONE = "Done"


# 1. ตั้งค่า Environment Variables (โหลดจาก .env)
load_dotenv()


print("กำลังดึงข้อมูลจากหลายแหล่ง...")

# 2. ดึงข้อมูลจาก Confluence
confluence_loader = ConfluenceLoader(
    url=os.environ["ATLASSIAN_URL"],
    username=os.environ["ATLASSIAN_USERNAME"],
    api_key=os.environ["ATLASSIAN_API_TOKEN"],
    space_key="SDRAG", # เปลี่ยนเป็น Space Key ใน Confluence ของคุณ
    limit=50
)
docs_confluence = confluence_loader.load()

# 3. ดึงข้อมูลจาก Jira
project: str = JiraProject.RKB2
status: str = JiraStatus.DONE
jira_jql: str = f"project = {project} AND status = '{status}'" # สร้าง JQL จาก Enum
jira_loader = JiraLoader(
    url=os.environ["ATLASSIAN_URL"],
    username=os.environ["ATLASSIAN_USERNAME"],
    api_key=os.environ["ATLASSIAN_API_TOKEN"],
    jql=jira_jql,
)
docs_jira = jira_loader.load()

# 4. ดึงข้อมูลจากไฟล์ Markdown
md_loader = TextLoader("architecture.md", encoding="utf-8")
docs_md = md_loader.load()

# รวมข้อมูลทั้ง 3 แหล่งเข้าด้วยกัน
all_docs = docs_confluence + docs_jira + docs_md
print(f"ดึงข้อมูลสำเร็จ! รวมทั้งหมด {len(all_docs)} Documents")

# 5. หั่นข้อมูล (Chunking)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_documents(all_docs)

# 6. สร้าง Vector Database ด้วย Ollama (nomic-embed-text)
print("กำลังสร้างฐานข้อมูล Vector...")
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 7. สร้าง Prompt และ RAG Chain ด้วย Ollama LLM (gemma4:12b)
template = """คุณคือ Senior Developer ของทีม ให้ตอบคำถามโดยอิงจากเอกสาร สเปก (Confluence) ประวัติการแก้ปัญหา (Jira) และโครงสร้างโปรเจกต์ (Markdown) ที่ให้มาเท่านั้น
Context:{context}
Question: {question}"""
prompt = ChatPromptTemplate.from_template(template)

llm = ChatOllama(model="gemma4:12b", temperature=0)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 8. ทดสอบใช้งาน
question = "บั๊กเกี่ยวกับปุ่ม Login ล่าสุดที่แก้ไปใน Jira มีสาเหตุจากอะไร และใน architecture.md บอกว่าระบบ Authentication เราเชื่อมกับอะไร?"
print(f"\nคำถาม: {question}")
print(f"\nคำตอบ:\n{rag_chain.invoke(question)}")