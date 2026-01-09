#     PR #4    

       , PR #4      .

## 1.  PR  (PR #4 ~ PR #10)

| PR |   |   |
|---|---|---|
| **PR #4** | **  RAG  ** | - **  **: , ,   <br>- ** **:  ,  ,  <br>- ** **: LangGraph    <br>- **  ** |
| **PR #5** | **     ** | - ** (Query Rewriting)**:       <br>- ** (Hybrid Search)**:  (BM25)   <br>- **  **: LLM      |
| **PR #6** | **    ** | - **  **: PostgreSQL   <br>- ** **:       <br>- **  **:         |
| **PR #7** | **     ()** | - **RAGAS  **: Faithfulness, Answer Relevancy, Context Precision  <br>- **  **:       <br>- ** **:     |
| **PR #8** | **    ** | - **  UI**:   "/"  <br>- **    **:     <br>- **A/B **:      |
| **PR #9** | **UI/UX ** | - **  **:     <br>- ** **:  , ,    <br>- **  **:  ,     |
| **PR #10** | ** , ,  ** | - ** **: , ,   <br>- ****:       <br>- ** **: , ,  ,    |

---

## 2. PR #4:   RAG  

PR #4 LangGraph     .

![Multi-Agent Workflow](https://i.imgur.com/example.png)  <!--    -->

### 2.1.    

|   |  |   |  |
|---|---|---|---|
| **/** |   ,    |   +   | 1 |
| **** |    (  ) |   | 2 |
| **/** |    (  ) |   | 3 (Fallback) |

### 2.2.  

1.  **Supervisor ( )**
    -           .
    -         .

2.  **Jurisdiction Agent (  )**
    -   ****:  
    -   ****: / DB   ,  (,  )    .
    -   ****:   ,  

3.  **Precedent Agent (  )**
    -   ****:  
    -   ****:  DB    .
    -   ****:    ( N)

4.  **Consultation Agent (  )**
    -   ****:  
    -   ****: / DB   .
    -   ****:    ( N)

### 2.3. LangGraph  (State Graph)

1.  **Start**:    (State) .

2.  **Route Query (Supervisor)**:      .
    -   "    ?" → `JurisdictionAgent`
    -   "~     ?" → `PrecedentAgent`

3.  **Execute `JurisdictionAgent`**:     .

4.  **Execute `PrecedentAgent`**:     .

5.  **Check for Precedents (Conditional Edge)**: `PrecedentAgent`    .
    -   ** **: `Generate Final Answer` .
    -   ** **: `ConsultationAgent`  (Fallback).

6.  **Execute `ConsultationAgent`**:     .

7.  **Generate Final Answer (Supervisor)**:    (, /)    .

8.  **End**:    .

       ,        .


---

## 3.  :    (Disclaimer)

        . LLM       ,    .

### 3.1.   

 LLM ( Supervisor)       .

> **:   **
> -  "100%   ", "  "     .
> -  "   ~    ", "   ~   "     .
> -       (Disclaimer) :
>   "      ,    .         ."

### 3.2. UI/UX 

-   "     ,   ."   .
-             .
