import csv
import argparse
from retrievers.semantic_scholar_paper import *
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import time

#获得当前时间下的日期
def get_time_current_begin_end():
    # 计算当前日期和半年前的日期
    current_date = datetime.now()
    half_year_ago = current_date - timedelta(weeks=26)

    # 格式化日期为arXiv接受的格式 (YYYYMMDD)
    #当前时间: 20241202
    #半年时间: 20240603
    current_date_str = current_date.strftime('%Y%m%d')
    half_year_ago_str = half_year_ago.strftime('%Y%m%d')
    return current_date_str,half_year_ago_str

def get_arxiv_paper(start_date,end_date,max_results=1000,max_retries=6,delay=1):
    # 初始起始位置
    start = 0
    all_articles = []  # 用于存储所有文章的列表
    retries=0
    while True:
        try:
            while retries<max_retries:
                # arXiv API查询URL，查询条件为计算机视觉 (cs.CV) 领域，按提交日期排序
                url = f"http://export.arxiv.org/api/query?search_query=cat:cs.CV AND submittedDate:[{start_date} TO {end_date}]&max_results={max_results}&start={start}&sortBy=submittedDate"
                # 发起API请求
                response =requests.get(url)
                # 如果请求失败，抛出异常
                response.raise_for_status()
                # 解析返回的XML数据
                root = ET.fromstring(response.text)
                # 提取每篇文章的信息
                articles = []
                for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                    title = entry.find('{http://www.w3.org/2005/Atom}title').text
                    title = title.replace("\n", "").strip()
                    articles.append(title)
                if(len(articles)!=0):
                    print(len(articles))
                    break
                else:
                    print(f"没有返回文章内容，将在 {delay} 秒后重新尝试...")
                    retries=retries+1
                    time.sleep(delay)
                    delay *= 2  # 指数替换
            if(retries>=max_retries):
                print("当前网络状态不好，已经超过最大重试次数！")
                break
            # 将当前请求的结果添加到所有文章列表中
            all_articles.extend(articles)
            if len(articles) < max_results and len(articles)>0:
                print("当前到达最后一页，检索完毕！")
                break
            start += max_results
            # 延时delay秒，避免过于频繁的请求
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"请求发生错误: {e}")
            break  # 如果发生错误，退出循环
        except Exception as e:
            print(f"发生了其他错误: {e}")
            break  # 如果发生其他错误，退出循环
    return all_articles

def if_published(paper_titles,base_citation_count,filename):
    for title in paper_titles:
        paper=S2paper(title,ref_type='title', filled_authors=True, force_return=False)
        if paper.citation_count is not None:
            if paper.citation_count < base_citation_count:  # 如果引用数量太少
                print(f"Citation_count is {paper.citation_count} which does not meet the requirement!")
                continue
        else:# 没有citation_count
            print("Citation_count is none!")
            continue

        if paper.publisher is not None:
            print(paper.publisher)
            if paper.publisher['name']=='arXiv.org':
                with open(filename, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    # 写入表头
                    writer.writerow(["paper_id", "title", "citation_count"])
                    for paper in papers:
                        # 获取每篇文章的 paper_id, title, citation_count
                        writer.writerow([paper.s2id, paper.title, paper.citation_count])
                        print(f"写入 {paper.s2id} - {paper.title} - {paper.citation_count}")

        else:
            print("Information about publisher is none!")

        time.sleep(1)

if __name__ == "__main__":
    # 创建一个 ArgumentParser 对象
    parser = argparse.ArgumentParser(description='查询 Arxiv 论文并判断是否经由会议期刊发布')

    # 添加命令行参数
    parser.add_argument('from_now', type=int, help="是否查询从今天起半年的文章")
    parser.add_argument('min_citation_count', type=int, help="至少需要满足的引用数量")
    parser.add_argument('start_date', type=str, help="查询的开始日期 (格式: YYYYMMDD)|如果from_now为1，则不会读取这里的数据~")
    parser.add_argument('end_date', type=str, help="查询的结束日期 (格式: YYYYMMDD)|如果from_now为1，则不会读取这里的数据~")
    parser.add_argument('max_results', type=int, help="每次请求的最大论文数")
    parser.add_argument('max_retries', type=int, help="每次请求的最大重试次数")
    parser.add_argument('delay', type=int, help="每次请求重试时的延迟次数")

    # 解析命令行参数
    args = parser.parse_args()

    if args.from_now:
        end_date,start_date=get_time_current_begin_end()
        print(start_date,end_date)
        filename = f"{start_date}_{end_date}"
        papers = get_arxiv_paper(start_date, end_date, args.max_results,args.max_retries,args.delay )
    else:
        filename= f"{args.start_date}_{args.end_date}"
        papers = get_arxiv_paper(args.start_date, args.end_date, args.max_results,args.max_retries,args.delay )

    if_published(papers,args.min_citation_count,filename)
