# AI Research Assistant — Thiết kế toàn bộ chức năng

## Tầm nhìn sản phẩm

> **Trợ lý nghiên cứu AI cá nhân** — mỗi sáng gửi paper hot nhất, cho phép hỏi đáp sâu,
> quản lý knowledge base cá nhân, tất cả qua Telegram.

---

## 4 Nhóm chức năng

```
 DAILY DIGEST     |   CHATBOT Q&A    |  KNOWLEDGE MGMT  |  CA NHAN HOA
 ---------------  | ---------------- | ----------------  | -----------
 Auto fetch paper |  Hoi ve paper    |  Reading list     |  Chon topic
 Loc + xep hang   |  So sanh paper   |  Luu & gan tag    |  Loc keyword
 Tom tat tieng    |  Giai thich      |  Tim kiem         |  Tan suat
 Viet             |  thuat ngu       |  trong kho        |  gui digest
 Gui Telegram     |  Hoi follow-up   |  Goi y paper      |  Ngon ngu
 7:00 sang        |  Tao outline     |  lien quan        |  tom tat
```

---

## NHOM 1: Daily Digest — Tu dong tong hop paper moi sang

### 1.1 Auto-fetch paper trending
- Moi sang 7:00, he thong tu dong lay paper moi tu arXiv
- Query theo topic nguoi dung cau hinh, loc 7 ngay gan nhat

### 1.2 Loc thong minh (Hybrid: Rule + LLM)
- Buoc 1: Loai paper chua keyword loai tru
- Buoc 2: LLM cham relevance_score 0-10 dua tren abstract
- Nguong: Giu paper co score >= 4.0

### 1.3 Xep hang & phan loai
- LLM danh gia: Novelty, practical value, clarity
- Phan loai: Must-read (>=8.0) / Worth skimming (>=5.5) / Archive

### 1.4 Tom tat tieng Viet co cau truc

```
 [Ten paper]
 arXiv link
 Score: 8.5/10 — Must-read

 Van de: ...
 Y tuong chinh: ...
 Phuong phap: ...
 Ket qua: ...
 Han che: ...
 Ai nen doc: ...
```

### 1.5 Xac minh chong hallucination
- Critic Agent doc lai paper excerpt + summary
- Neu fail: tu viet lai summary bao thu hon
- Muc dich: dam bao ban tom tat TRUNG THUC voi paper goc

### 1.6 Gui qua Telegram
- Format dep voi emoji, phan loai Must-read / Worth skimming
- Inline commands: /detail_N, /ask_N

---

## NHOM 2: Chatbot Q&A — Tuong tac hoi dap ve paper

### 2.1 Hoi ve 1 paper cu the
```
User: /ask_1
Bot:  Ban muon hoi gi ve paper "ReAct: Synergizing..."?

User: paper nay khac gi so voi chain-of-thought?
Bot:  Theo paper, ReAct ket hop reasoning VA acting...
      [trich dan doan relevant tu paper]
      Nguon: Section 3.2, trang 5
```

**Co che (RAG):**
1. Noi dung paper da duoc chunk + embedding -> luu ChromaDB
2. Cau hoi user -> embedding -> tim top-k chunks lien quan
3. LLM nhan chunks + cau hoi -> sinh cau tra loi + trich nguon

### 2.2 So sanh 2-3 papers
```
User: so sanh paper 1 va paper 3
Bot:  Bang so sanh: Van de / Phuong phap / Diem manh / Diem yeu / Khi nao nen dung
```

### 2.3 Giai thich thuat ngu / concept
```
User: RAG la gi?
Bot:  RAG (Retrieval-Augmented Generation): ky thuat ket hop tim kiem voi sinh text...
      Cac paper hom nay co lien quan den RAG: Paper 2 (score 8.1), Paper 5 (score 7.3)
```

### 2.4 Hoi follow-up (multi-turn conversation)
- Bot nho lich su hoi thoai trong phien
- Co che: LangChain ConversationBufferMemory

### 2.5 Tao outline / literature review
```
User: tao outline literature review ve multi-agent systems tu cac paper tuan nay
Bot:  Literature Review Outline:
      1. Introduction
      2. Approaches (2.1 Centralized, 2.2 Decentralized, 2.3 Hierarchical)
      3. Key Findings
      4. Open Challenges
```

### 2.6 Tom tat lai theo yeu cau rieng
```
User: tom tat paper 3 duoi dang 5 bullet points, danh cho nguoi khong chuyen
Bot:  5 diem chinh (de hieu): ...
```

---

## NHOM 3: Knowledge Management — Quan ly kho tri thuc

### 3.1 Reading List
```
/save 2        -> Luu paper vao reading list
/readlist      -> Xem danh sach doc
/done 1        -> Danh dau da doc
```

### 3.2 Gan tag & ghi chu
```
/tag 2 RAG implementation    -> Gan tag
/note 2 Can thu reproduce    -> Ghi chu
/search RAG                  -> Tim paper theo tag
```

### 3.3 Tim paper lien quan
```
/related 2     -> Tim paper tuong tu trong kho + arXiv moi
```

### 3.4 Weekly/Monthly Report
```
/report week   -> Thong ke: tong paper, xu huong, paper tuong tac nhieu nhat
```

---

## NHOM 4: Ca nhan hoa

### 4.1 Quan ly chu de
```
/topics             -> Xem danh sach chu de
/topic_add <topic>  -> Them chu de
/topic_remove <num> -> Xoa chu de
```

### 4.2 Cau hinh digest
```
/settings      -> Xem cai dat
/set_time 08:30
/set_max 3
/set_lang en
```

---

## Kien truc Multi-Agent (LangGraph)

```
                        User (Telegram)
                             |
                    [Supervisor Agent]
                    Phan tich intent
                    -> chon agent phu hop
                   /        |         \
                  /         |          \
    [Daily Pipeline]   [Q&A RAG]    [Tool Agents]
    Source -> Filter    Retriever    Search Agent
    -> Rank -> Read     -> Answer   Compare Agent
    -> Summary          -> Citation Report Agent
    -> Critic                       Export Agent
       |  ^
       |  | (fail -> retry)
       v  |
    -> Delivery

    ChromaDB <-- Reader Agent (luu embedding)
    ChromaDB --> Retriever (tim kiem)
    SQLite <--> Pipeline + Tool Agents
```

### Tai sao day la multi-agent THAT:

| Dac diem                    | Co trong he thong                              |
|-----------------------------|------------------------------------------------|
| Supervisor dieu phoi        | Phan tich user intent -> route den dung agent   |
| Cycle (vong lap)            | Critic Agent reject -> Summary Agent viet lai   |
| Quyet dinh tu chu           | Supervisor tu chon agent nao xu ly              |
| Shared state                | Tat ca agent doc/ghi vao cung ChromaDB + SQLite |
| Tool-use                    | Q&A Agent tu chon: tim DB, tim arXiv, hoac memory |
| Human-in-the-loop           | User can thiep qua Telegram commands            |

---

## Tong hop Telegram Commands

| Command          | Chuc nang                         | Nhom        |
|------------------|-----------------------------------|-------------|
| /start           | Gioi thieu bot                    | —           |
| /today           | Xem lai digest hom nay            | Digest      |
| /detail_N        | Xem tom tat chi tiet paper N      | Digest      |
| /ask             | Bat dau hoi dap tu do             | Q&A         |
| /ask_N           | Hoi ve paper N cu the             | Q&A         |
| /compare N M     | So sanh paper N va M              | Q&A         |
| /explain <term>  | Giai thich thuat ngu              | Q&A         |
| /outline         | Tao literature review outline     | Q&A         |
| /save N          | Luu paper N vao reading list      | Knowledge   |
| /readlist        | Xem danh sach doc                 | Knowledge   |
| /done N          | Danh dau da doc                   | Knowledge   |
| /tag N <tags>    | Gan tag cho paper                 | Knowledge   |
| /note N <text>   | Ghi chu cho paper                 | Knowledge   |
| /search <query>  | Tim paper trong kho               | Knowledge   |
| /related N       | Tim paper lien quan               | Knowledge   |
| /report week     | Bao cao tuan                      | Knowledge   |
| /topics          | Xem/sua chu de                    | Settings    |
| /topic_add <t>   | Them chu de                       | Settings    |
| /settings        | Xem cai dat                       | Settings    |
| /help            | Tro giup                          | —           |

---

## Lo trinh phat trien

### Phase 1 — Core (tuan 1-2)
- [ ] Refactor pipeline: bo n8n, dung APScheduler
- [ ] Tich hop LangChain + Ollama
- [ ] ChromaDB: luu paper embeddings
- [ ] Telegram Bot co ban: nhan digest + /today
- [ ] Critic Agent voi vong lap self-correction

### Phase 2 — Chatbot Q&A (tuan 3-4)
- [ ] RAG pipeline: user hoi -> retrieval -> answer
- [ ] Multi-turn conversation (memory)
- [ ] /ask, /ask_N, /explain commands
- [ ] /compare — so sanh papers
- [ ] LangGraph: Supervisor routing

### Phase 3 — Knowledge & Polish (tuan 5-6)
- [ ] Reading list: /save, /readlist, /done
- [ ] Tag & search: /tag, /search
- [ ] /report — thong ke tuan
- [ ] /settings — ca nhan hoa
- [ ] Demo recording + documentation

> Phase 1 da du de demo co ban.
> Phase 2 la phan an tuong nhat (chatbot live).
> Phase 3 la bonus.
