# 交易复盘 MVP 网页版

这是一个可直接部署的静态网页目录。上传整个文件夹后，电脑和手机都可以通过同一个网址访问。

所有复盘内容默认保存在当前浏览器本地。跨设备访问同一个网址没有问题，但数据不会自动同步；需要用页面右上角的“导出复盘”备份，或后续升级到账号 + 云端数据库。

## 部署方式

最简单的方式：

1. 打开 Netlify Drop：`https://app.netlify.com/drop`
2. 把整个 `trade-review-mvp` 文件夹拖进去
3. 等它生成网址

也可以部署到 Vercel、GitHub Pages、Cloudflare Pages 或任意静态网站空间。目录里已经包含 `vercel.json` 和 `netlify.toml`。

部署后，用手机浏览器打开网址，可以添加到主屏幕，当作一个轻量 App 使用。

## 交易单 Excel / CSV

支持券商导出的 `.xlsx`、`.xls`、`.csv` 和 `.txt` 文件。网页会自动寻找表头和包含成交记录的工作表，常见中文或英文字段名都可以识别。

至少需要日期、证券代码、买卖方向和成交价格等信息，例如：

```csv
日期,证券代码,证券名称,买卖方向,成交数量,成交价格,成交金额
2026-05-13,NVDA,NVIDIA,买入,80,132.20,10576
2026-05-29,NVDA,NVIDIA,卖出,140,128.70,18018
```

也支持类似 `date,code,name,side,qty,price,amount` 的英文字段。

## 日线 CSV 可选

如果没有导入日线，页面会用交易价附近生成演示 K 线，方便先复盘流程。导入真实日线时建议字段：

```csv
date,code,open,high,low,close,volume
2026-05-13,NVDA,129.2,133.8,128.4,132.2,280000000
```

## 收盘后自动更新行情

仓库包含 GitHub Actions 自动任务：

- 亚洲市场：工作日北京时间 20:30 左右更新。
- 美国市场：周二至周六北京时间 12:00 左右更新前一交易日数据。
- 网页会自动读取 `data/market.json` 和 `data/intraday.json`。
- 默认获取约400天日 K；套餐允许时同时获取约400天5分钟分时。
- 双击这段范围内的日 K，有真实5分钟数据就显示当天分时；没有权限或数据源缺失时会明确提示。

先在仓库的 `Settings > Secrets and variables > Actions` 中添加：

```text
EODHD_API_TOKEN
```

然后编辑 `market-symbols.json` 的 `symbols`。`code` 必须与交割单中的证券代码完全一致，`eodhd` 是 EODHD 行情代码：

```json
{
  "symbols": [
    {
      "code": "600519",
      "eodhd": "600519.SHG",
      "name": "贵州茅台",
      "session": "asia"
    },
    {
      "code": "00700",
      "eodhd": "0700.HK",
      "name": "腾讯控股",
      "session": "asia"
    },
    {
      "code": "AAPL",
      "eodhd": "AAPL.US",
      "name": "Apple",
      "session": "us"
    }
  ],
  "historyDays": 400,
  "intradayDays": 400
}
```

常用后缀：

- 上海 A 股：`.SHG`
- 深圳 A 股：`.SHE`
- 港股：`.HK`，EODHD 代码通常使用4位数字，例如腾讯为 `0700.HK`
- 美股：`.US`

手动更新：进入 GitHub 仓库的 `Actions > Update market data > Run workflow`，选择 `all` 后运行。免费账户若没有分时权限，可勾选 `Update daily K only`，只更新日 K。

也可以每天从交割单中临时选择：

1. 在复盘网页导入交割单。
2. 点击 `选择行情股票`。
3. 勾选1至3只股票，点击 `复制清单`。
4. 点击 `打开更新任务`。
5. 在 GitHub 点击 `Run workflow`。
6. 把清单粘贴到 `Paste the list copied from the review website (1-3 stocks)`。
7. 再点击绿色 `Run workflow`。
8. 等任务完成后回到网页，点击 `读取最新行情`。

每次选择的股票会获取约400天日 K，以及套餐允许时约400天的5分钟分时。双击这段范围内的日 K，可查看当天分时。

这份临时清单只用于当次运行，不会改动 `market-symbols.json`。第二天可以选择另外三只，之前已经下载的历史行情仍会保留。

注意：公开仓库中的 `market-symbols.json` 和生成的行情数据所有人都能看到。不要上传交割单、账号、成交数量或成交金额。

## 当前 MVP 范围

- 导入不同券商导出的 Excel 或 CSV 交易单
- 自动汇总交易过的股票
- K 线显示价格、MA5、MA20、成交量
- 红点买入、蓝点卖出，可隐藏
- 双击日 K 查看当日分时线
- 按股票保存复盘记录
- 手动维护市场主线、持续性、爆发力、触发因素和轮动节奏
- 支持部署成网页，支持手机端自适应和基础离线缓存
