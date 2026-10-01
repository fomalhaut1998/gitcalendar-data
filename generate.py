#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GitHub 贡献日历抓成一个静态 JSON，供 hexo-filter-gitcalendar 直接读取。

输出格式是插件的硬性要求，别改：
{
  "total": 4,
  "contributions": [ [ {"date": "YYYY-MM-DD", "count": 0} x N ] x 53 ]
}
- 外层必须正好 53 个元素：第 0 个是最早一周，第 52 个是本周（插件靠 [0]/[47]/[48]/[51]/[52] 定位）
- 每天只需要 date 和 count 两个字段
- total 必须是纯数字

任何一项对不上就直接退出、不覆写 data.json —— 保留上一次的好数据，比写进一份坏数据强。
"""
import json
import os
import sys
import urllib.request

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
USER = os.environ.get("GH_USER", "fomalhaut1998")
OUT = os.environ.get("OUT", "data.json")

QUERY = """
query ($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "gitcalendar-data-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def build(payload):
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]

    weeks = [
        [{"date": d["date"], "count": d["contributionCount"]} for d in w["contributionDays"]]
        for w in calendar["weeks"]
    ]
    weeks = [w for w in weeks if w]
    if len(weeks) > 53:
        weeks = weeks[-53:]
    if len(weeks) != 53:
        raise SystemExit("周数不对：%d（期望 53），本次不覆写 %s" % (len(weeks), OUT))
    if not weeks[52]:
        raise SystemExit("最后一周是空的，本次不覆写 %s" % OUT)

    total = calendar["totalContributions"]
    count_sum = sum(d["count"] for w in weeks for d in w)
    if total != count_sum:
        print("提示：totalContributions=%s 与按天累加=%s 不一致（尾部有零星天数落在 53 周之外），以官方数字为准" % (total, count_sum))

    return {"total": total, "contributions": weeks}


def main():
    if not TOKEN:
        raise SystemExit("缺少 GH_TOKEN / GITHUB_TOKEN 环境变量")
    payload = graphql(QUERY, {"login": USER})
    if payload.get("errors"):
        raise SystemExit("GraphQL 报错：%s" % payload["errors"])
    if not payload.get("data", {}).get("user"):
        raise SystemExit("GraphQL 没返回 user 节点：%s" % json.dumps(payload)[:300])

    data = build(payload)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body)
    print("已写出 %s：%d 字节 · %d 周 · total=%s" % (OUT, len(body.encode("utf-8")), len(data["contributions"]), data["total"]))


if __name__ == "__main__":
    main()
