/*
 * 场景句库（手写内容，可直接编辑）
 *
 * 每个场景 scene:
 *   id / name / icon / tip（文化提示）/ dialogs（关联的完整对话 id，来自 dialogs.js）
 *   sections: [{ title, items: [...] }]
 *
 * 每条 item 二选一：
 *   { s: "我要说的英文", z: "中文" }
 *   { h: "对方会说的英文", z: "中文", f: "实际听起来像（可选）", r: ["我可以回的英文", "中文"]（可选） }
 */
window.PHRASES = {
  rescue: {
    id: "rescue",
    name: "救命句",
    icon: "🆘",
    tip: "听不懂不丢人，美国人很习惯和外国人打交道。先说一句 Sorry, could you say that again? 对方一般会放慢、换个说法。",
    sections: [
      {
        title: "听不懂的时候",
        items: [
          { s: "Sorry, could you say that again?", z: "不好意思，能再说一遍吗？" },
          { s: "Could you speak a little slower, please?", z: "能说慢一点吗？" },
          { s: "Sorry, I didn't catch that.", z: "抱歉，我没听清。" },
          { s: "What does that mean?", z: "那是什么意思？" },
          { s: "Could you write it down for me?", z: "能帮我写下来吗？" },
          { s: "Could you show me on my phone?", z: "能在我手机上指给我看吗？" },
          { s: "Do you mean this one?", z: "你是说这个吗？" },
          { s: "My English isn't very good. Sorry.", z: "我英语不太好，不好意思。" },
          { s: "Can I use my phone to translate?", z: "我可以用手机翻译一下吗？" },
        ],
      },
      {
        title: "万能回答",
        items: [
          { s: "Yes, please.", z: "好的，麻烦了。（接受）" },
          { s: "No, thank you.", z: "不用了，谢谢。" },
          { s: "I'm good, thanks.", z: "不用了，谢谢。（最常用的口语拒绝）" },
          { s: "That's it.", z: "就这些。" },
          { s: "Just a second, please.", z: "请稍等一下。" },
          { s: "Let me check.", z: "我看一下。" },
          { s: "Sounds good.", z: "好的 / 可以。" },
          { s: "No worries.", z: "没关系 / 不客气。" },
        ],
      },
      {
        title: "求助",
        items: [
          { s: "Excuse me, can you help me?", z: "打扰一下，能帮我一下吗？" },
          { s: "Where is the restroom?", z: "洗手间在哪里？" },
          { s: "Excuse me, can I get by?", z: "不好意思，借过一下。" },
          { s: "Sorry, I'm new here.", z: "不好意思，我刚来这里。" },
          { s: "I need help. Please call 911.", z: "我需要帮助，请打 911。" },
        ],
      },
    ],
  },

  scenes: [
    // ------------------------------------------------------------
    {
      id: "bank_open",
      name: "银行开户",
      icon: "📝",
      tip: "带齐这些再去：① 护照（连同签证 / I-94）② 第二证件：美国驾照、州 ID 等 ③ 地址证明：租房合同、水电账单、寄到家里的信件 ④ SSN 或 ITIN（没有的话先打电话问能不能开）⑤ 首笔存款，几十到几百美元。最好先在银行官网或 App 上预约（appointment）。银行会问你的职业、雇主、收入、钱从哪来、会不会有国际汇款，这是问每个人的反洗钱标准问题，如实回答就行。Overdraft（透支保护）建议拒绝，透支一次常收约 35 美元。走之前拿到 account number（账号）和 routing number（银行路由号），交给公司 HR 设置工资入账。",
      dialogs: ["bank_open_account", "bank_open_questions"],
      sections: [
        {
          title: "去之前：预约 / 问清楚",
          items: [
            { s: "Hi, I'd like to make an appointment to open a checking account.", z: "你好，我想预约开一个日常（支票）账户。" },
            { s: "Do I need an appointment, or can I just walk in?", z: "需要预约吗，还是直接去就行？" },
            { s: "What documents do I need to bring?", z: "我需要带哪些材料？" },
            { s: "Can I open an account without a Social Security number?", z: "没有社安号能开户吗？" },
            { s: "Do you have a checking account with no monthly fee?", z: "你们有不收月费的日常账户吗？" },
            { h: "What day and time work best for you?", z: "哪天几点对你最方便？", r: ["Tomorrow afternoon, if possible.", "可以的话明天下午。"] },
            { h: "Please bring two forms of ID and proof of address.", z: "请带两种证件和地址证明。" },
            { h: "You'll get a confirmation email shortly.", z: "你很快会收到一封确认邮件。" },
          ],
        },
        {
          title: "到了银行",
          items: [
            { s: "Hi, I have a two o'clock appointment to open an account. My name is Li Wang.", z: "你好，我约了两点开户，我叫王力。" },
            { s: "Hi, I'd like to open a checking account. I don't have an appointment.", z: "你好，我想开日常账户，我没有预约。" },
            { s: "My English is limited, so please speak slowly. Thank you!", z: "我英语有限，请说慢一点，谢谢！" },
            { h: "How can I help you today?", z: "今天要办什么业务？", r: ["I'd like to open a checking account.", "我想开一个日常（支票）账户。"] },
            { h: "Do you have an appointment?", z: "您有预约吗？", r: ["No, I'm a walk-in.", "没有，我是直接来的。"] },
            { h: "Have a seat. A banker will be right with you.", z: "请坐，客户经理马上来。" },
            { h: "It'll be about a fifteen-minute wait. Is that okay?", z: "大概要等 15 分钟，可以吗？", r: ["That's fine. I'll wait.", "没关系，我等。"] },
          ],
        },
        {
          title: "证件 / 联系方式",
          items: [
            { h: "I'll need two forms of ID and proof of address.", z: "需要两种证件和地址证明。", r: ["Here's my passport and my lease.", "这是我的护照和租房合同。"] },
            { h: "Do you have a Social Security number?", z: "您有社安号吗？", r: ["No, but I have an ITIN.", "没有，但我有 ITIN（税号）。"] },
            { h: "What's your current address?", z: "你现在的地址是？", r: ["It's 125 Oak Street, Apartment 3B.", "Oak 街 125 号，3B 公寓。"] },
            { h: "How long have you lived at this address?", z: "你在这个地址住了多久？", r: ["About two months.", "大概两个月。"] },
            { h: "What's the best phone number to reach you?", z: "联系你最好用哪个电话号码？" },
            { h: "And your email address?", z: "邮箱地址呢？" },
            { s: "I just moved here, so I don't have a utility bill yet. Is my lease okay?", z: "我刚搬来，还没有水电账单。租房合同可以吗？" },
            { s: "I don't have a U.S. driver's license yet. What else can I use?", z: "我还没有美国驾照，还能用什么证件？" },
            { s: "Could you spell that for me?", z: "能帮我拼一下吗？" },
          ],
        },
        {
          title: "背景问题（每个人都会被问）",
          items: [
            { h: "These are just standard questions we ask everyone.", z: "这些是我们问每个人的标准问题。" },
            { h: "Are you a U.S. citizen?", z: "你是美国公民吗？", r: ["No, I'm not.", "不是。"] },
            { h: "Are you a permanent resident?", z: "你是永久居民（绿卡）吗？", r: ["No, I'm here on a work visa.", "不是，我持工作签证。"] },
            { h: "What's your country of citizenship?", z: "你是哪国国籍？", r: ["China.", "中国。"] },
            { h: "What's your occupation?", z: "你的职业是什么？", r: ["I'm an electrical engineer.", "我是电气工程师。"] },
            { h: "Who's your employer?", z: "你的雇主（公司）是谁？", f: "Who's your employer?（employer = 雇主/公司）", r: ["I work for ABC Company.", "我在 ABC 公司工作。"] },
            { h: "What's your annual income?", z: "你的年收入是多少？", r: ["It's around eighty thousand dollars.", "大约八万美元。"] },
            { h: "What will you mainly use this account for?", z: "这个账户主要用来做什么？", r: ["Getting my paycheck and paying bills.", "收工资和付账单。"] },
            { h: "Where will the money in this account come from?", z: "账户里的钱主要从哪来？（资金来源）", f: "What's the source of funds?（另一种问法）", r: ["Mostly from my salary.", "主要是我的工资。"] },
            { h: "How much do you expect to deposit each month?", z: "你预计每月存入多少钱？", r: ["About five thousand dollars.", "大约五千美元。"] },
            { h: "Do you expect to send or receive international wires?", z: "你会有国际汇款进出吗？", r: ["Yes, sometimes, to my family in China.", "会，偶尔汇给国内的家人。"] },
            { h: "Have you ever had a bank account closed?", z: "你有过银行账户被关闭的情况吗？", r: ["No, never.", "没有。"] },
          ],
        },
        {
          title: "选账户 / 问费用",
          items: [
            { h: "Which account would you like to open?", z: "你想开哪种账户？", r: ["A basic checking account, please.", "基础日常账户。"] },
            { s: "What's the difference between these two accounts?", z: "这两种账户有什么区别？" },
            { s: "Is there a monthly fee?", z: "有月费吗？" },
            { s: "How can I avoid the monthly fee?", z: "怎么才能免月费？" },
            { h: "It's waived if you set up direct deposit.", z: "设置工资直接入账就免（月费）。" },
            { s: "What's the minimum balance?", z: "最低余额要求是多少？" },
            { s: "Are there any other fees I should know about?", z: "还有其他我该知道的费用吗？" },
            { h: "Would you like overdraft protection?", z: "要开透支保护吗？（透支一次常收约 35 美元，建议拒绝）", r: ["No, thank you. Please decline it.", "不用，谢谢，请帮我拒绝。"] },
            { h: "Would you like to open a savings account as well?", z: "要不要同时开一个储蓄账户？", r: ["Not right now, thanks.", "暂时不用，谢谢。"] },
            { h: "Are you interested in a credit card?", z: "有兴趣办信用卡吗？", r: ["Not today. Maybe later.", "今天先不办，以后再说。"] },
            { s: "I'm new to the U.S. and don't have a credit history. Do you have a secured credit card?", z: "我刚来美国，没有信用记录。你们有担保信用卡吗？（存押金办卡，用来积累信用）" },
          ],
        },
        {
          title: "存首笔钱 / 签字",
          items: [
            { h: "How much would you like to deposit to open the account?", z: "开户要存多少钱？", r: ["Five hundred dollars in cash.", "500 美元现金。"] },
            { h: "There's a twenty-five-dollar minimum opening deposit.", z: "开户最低要存 25 美元。" },
            { h: "Please review this and sign here.", z: "请看一下这份文件，然后在这里签名。" },
            { h: "Initial here, and sign at the bottom.", z: "这里签名缩写，底下签全名。", f: "Initial here（initial = 姓名首字母，例如 Li Wang 写 LW）" },
            { s: "Could you give me a minute to read this?", z: "能给我一分钟看一下吗？" },
            { s: "Can I get a copy of this?", z: "能给我一份复印件吗？" },
            { h: "Would you like paperless statements?", z: "要电子账单吗？", r: ["Yes, please.", "要，谢谢。"] },
          ],
        },
        {
          title: "拿卡 / 网银 / 收尾",
          items: [
            { h: "Please enter a four-digit PIN.", z: "请输入一个四位数密码。" },
            { h: "Please enter it one more time to confirm.", z: "请再输入一次确认。" },
            { h: "Here's a temporary card you can use today.", z: "这是一张临时卡，今天就能用。" },
            { s: "When will I get my debit card?", z: "借记卡什么时候能拿到？" },
            { h: "Your card will arrive in the mail in seven to ten business days.", z: "卡会在 7 到 10 个工作日内寄到。" },
            { s: "Can I get my account number and routing number? I need them for direct deposit.", z: "能给我账号和路由号吗？设置工资入账要用。" },
            { s: "Can you print a direct deposit form for me?", z: "能帮我打印一张工资直接入账表吗？" },
            { s: "Could you help me set up the mobile app?", z: "能帮我设置一下手机 App 吗？" },
            { s: "Can I set up Zelle today?", z: "今天能开通 Zelle 吗？" },
            { h: "Here's my business card. Call me if you have any questions.", z: "这是我的名片，有问题打给我。", r: ["Thank you so much for your help!", "非常感谢你的帮助！"] },
          ],
        },
      ],
    },

    // ------------------------------------------------------------
    {
      id: "bank",
      name: "银行",
      icon: "🏦",
      tip: "开户请看“银行开户”场景。存支票要在背面签名，存进去的钱有时要过几天才能用（hold）。转账常用 Zelle。打客服电话听到语音菜单，直接说 “Representative” 可转人工。银行不会主动打电话问你的 PIN 或验证码，有人问就是诈骗。",
      dialogs: ["bank_card_problem"],
      sections: [
        {
          title: "柜台：存钱 / 取钱",
          items: [
            { s: "I'd like to deposit this check.", z: "我想存这张支票。" },
            { s: "I'd like to withdraw five hundred dollars.", z: "我想取 500 美元。" },
            { s: "I'd like to deposit some cash.", z: "我想存一些现金。" },
            { h: "Can I see your ID?", z: "能看下您的证件吗？" },
            { h: "Please sign the back of the check.", z: "请在支票背面签名（背书）。" },
            { h: "How would you like your cash?", z: "现金要什么面额的？", r: ["Twenties, please.", "要 20 块的。"] },
            { h: "Large bills or small bills?", z: "要大面额还是小面额？", r: ["Small bills, please.", "小面额。"] },
            { h: "There's a hold on this check. The funds will be available on Thursday.", z: "这张支票有冻结期，钱周四才能用。", r: ["Why is there a hold?", "为什么会冻结？"] },
            { s: "Can I get a cashier's check?", z: "我能开一张本票吗？（交房租押金常用）" },
            { s: "What's my current balance?", z: "我现在的余额是多少？" },
          ],
        },
        {
          title: "卡 / 账户出问题",
          items: [
            { s: "My card was declined.", z: "我的卡被拒了。" },
            { s: "I lost my debit card.", z: "我的借记卡丢了。" },
            { s: "I see a charge I don't recognize.", z: "我看到一笔我不认识的消费。" },
            { s: "Can you lock my card?", z: "能帮我冻结这张卡吗？" },
            { s: "I forgot my PIN.", z: "我忘了密码。" },
            { s: "I can't log in to the app.", z: "我登录不了 App。" },
            { s: "I need to update my address.", z: "我要更新我的地址。" },
            { h: "Did you authorize this transaction?", z: "这笔交易是您本人授权的吗？", r: ["No, I didn't make that purchase.", "不是，我没买过这个。"] },
            { h: "I've locked your card and ordered a new one.", z: "我已经冻结了您的卡，并给您补办了新卡。" },
            { h: "We'll file a dispute and give you a temporary credit.", z: "我们会提交争议申诉，先给您临时退款。" },
            { h: "We'll text a one-time code to your phone.", z: "我们会给您手机发一个一次性验证码。（只在 App/网页里输入，任何来电索要验证码都是诈骗）" },
          ],
        },
        {
          title: "打客服电话",
          items: [
            { h: "Please say or enter your account number.", z: "请说出或输入您的账号。（语音菜单）" },
            { s: "Representative.", z: "人工客服。（对着语音菜单说，转人工）" },
            { h: "Your call may be recorded for quality assurance.", z: "通话可能会被录音以保证服务质量。" },
            { h: "Thank you for holding. Who am I speaking with?", z: "感谢等待。请问您是哪位？", r: ["Hi, this is Li Wang.", "你好，我是王力。"] },
            { h: "Can you verify your date of birth?", z: "能核实一下您的出生日期吗？", r: ["It's March fifth, nineteen eighty-five.", "1985 年 3 月 5 日。"] },
            { h: "Can you verify the last four digits of your Social?", z: "能核实一下社安号后四位吗？", f: "last four of your Social（Social 指 Social Security number）" },
            { h: "Is there anything else I can help you with?", z: "还有别的要帮忙的吗？", r: ["No, that's it. Thanks for your help.", "没有了，谢谢你的帮助。"] },
            { s: "Could you speak a little slower? English is my second language.", z: "能说慢一点吗？英语是我的第二语言。" },
          ],
        },
        {
          title: "转账 / ATM",
          items: [
            { s: "How do I send money with Zelle?", z: "怎么用 Zelle 转账？" },
            { s: "Can I send a wire transfer overseas?", z: "能往国外电汇吗？" },
            { s: "What's the fee for an international wire?", z: "国际电汇手续费多少？" },
            { s: "Is there an ATM nearby?", z: "附近有 ATM 吗？" },
            { s: "The ATM kept my card.", z: "ATM 把我的卡吞了。" },
            { h: "You'll be charged a three-dollar fee. Do you want to continue?", z: "将收取 3 美元手续费，是否继续？（非本行 ATM 提示）" },
          ],
        },
      ],
    },

    // ------------------------------------------------------------
    {
      id: "supermarket",
      name: "超市",
      icon: "🛒",
      tip: "结账时收银员几乎都会问：东西找到了吗、有没有会员卡、要不要袋子。刷卡多数是 tap（贴一下）或 insert（插卡），Apple Pay 基本都能用。买酒会查 ID。",
      dialogs: ["supermarket_find", "self_checkout", "supermarket_return"],
      sections: [
        {
          title: "找东西",
          items: [
            { s: "Excuse me, where can I find the eggs?", z: "打扰一下，鸡蛋在哪里？" },
            { s: "Which aisle is the rice in?", z: "大米在几号通道？" },
            { s: "Do you have oat milk?", z: "你们有燕麦奶吗？" },
            { s: "Is this on sale?", z: "这个在打折吗？" },
            { s: "How much is this?", z: "这个多少钱？" },
            { h: "It's in aisle five, on your left.", z: "在 5 号通道，你左手边。" },
            { h: "We're out of stock right now.", z: "现在缺货了。", r: ["When will you get more?", "什么时候补货？"] },
            { h: "Let me check in the back.", z: "我去后面仓库看一下。" },
          ],
        },
        {
          title: "熟食柜台 / 称重",
          items: [
            { h: "What can I get for you?", z: "要点什么？", f: "Whad-can-I-get-for-ya?" },
            { s: "Can I get half a pound of turkey, please?", z: "我要半磅火鸡肉。" },
            { s: "Sliced thin, please.", z: "切薄一点。" },
            { h: "Is this okay?", z: "这样（这个量/厚度）可以吗？", r: ["That's perfect.", "正好。"] },
            { h: "Anything else?", z: "还要别的吗？", r: ["That's it, thanks.", "就这些，谢谢。"] },
          ],
        },
        {
          title: "结账：收银员会问",
          items: [
            { h: "Did you find everything okay?", z: "东西都找到了吗？", f: "Didja find everything okay?", r: ["Yes, thanks.", "找到了，谢谢。"] },
            { h: "Do you have a rewards card with us?", z: "你有我们的会员卡吗？", r: ["No, I don't.", "没有。"] },
            { h: "What's your phone number?", z: "你的电话号码是多少？（查会员）", r: ["I don't have an account.", "我没有账号。"] },
            { h: "Do you need a bag?", z: "要袋子吗？", f: "Ya need a bag?", r: ["No, I'm good.", "不用了。"] },
            { h: "Paper or plastic?", z: "纸袋还是塑料袋？", r: ["Plastic is fine.", "塑料袋就行。"] },
            { h: "Go ahead and tap or insert your card.", z: "可以贴卡或者插卡了。" },
            { h: "Debit or credit?", z: "借记卡还是信用卡？", r: ["Credit.", "信用卡。"] },
            { h: "Do you want any cash back?", z: "要取现金吗？（借记卡才有）", r: ["No, thanks.", "不用，谢谢。"] },
            { h: "Would you like to round up for charity today?", z: "要不要把零头凑整捐给慈善？", r: ["Not today, thanks.", "今天不用了，谢谢。"] },
            { h: "Do you want your receipt?", z: "要小票吗？", r: ["Yes, please.", "要，谢谢。"] },
            { h: "Can I see your ID?", z: "能看下你的证件吗？（买酒）" },
            { h: "Have a good one!", z: "祝你愉快！", r: ["You too!", "你也是！"] },
          ],
        },
        {
          title: "结账：我要说",
          items: [
            { s: "Can I pay with Apple Pay?", z: "可以用 Apple Pay 吗？" },
            { s: "Can I get a bag, please?", z: "能给我一个袋子吗？" },
            { s: "Sorry, I think this rang up wrong. It's on sale.", z: "不好意思，这个好像扫错价了，它在打折。" },
            { s: "Can you take this off? I don't want it.", z: "这个能去掉吗？我不要了。" },
          ],
        },
        {
          title: "自助结账",
          items: [
            { h: "Unexpected item in the bagging area.", z: "装袋区有未识别物品。（机器提示）" },
            { h: "Please wait for assistance.", z: "请等待工作人员协助。（机器提示）" },
            { s: "Excuse me, the machine needs help.", z: "打扰一下，这台机器需要帮忙。" },
            { s: "How do I weigh these bananas?", z: "香蕉怎么称重？" },
          ],
        },
        {
          title: "退换货",
          items: [
            { s: "I'd like to return this.", z: "我想退这个。" },
            { h: "Do you have the receipt?", z: "有小票吗？", r: ["Yes, here it is.", "有，给你。"] },
            { h: "Would you like a refund or an exchange?", z: "退款还是换货？", r: ["A refund, please.", "退款，谢谢。"] },
            { h: "It'll go back on your card in a few days.", z: "钱几天后退回你卡上。" },
          ],
        },
      ],
    },

    // ------------------------------------------------------------
    {
      id: "restaurant",
      name: "餐馆",
      icon: "🍽️",
      tip: "坐下吃饭的餐厅要付小费，一般 18%–20%，写在账单的 Tip 一栏。服务员问 How is everything? 只是客套，说 Great, thanks 就行。吃不完说 Can I get a box? 打包。快餐店不需要小费。",
      dialogs: ["restaurant_ordering", "restaurant", "starbucks", "drive_thru", "tipping_guide"],
      sections: [
        {
          title: "进门等位",
          items: [
            { h: "How many?", z: "几位？", r: ["Just two.", "两位。"] },
            { h: "How many in your party?", z: "你们几位？", r: ["Just one.", "就我一个。"] },
            { h: "Do you have a reservation?", z: "有预订吗？", r: ["No, we don't.", "没有。"] },
            { h: "It'll be about a twenty-minute wait.", z: "大概要等 20 分钟。", r: ["That's fine. We'll wait.", "没关系，我们等。"] },
            { h: "Can I get a name?", z: "留个名字？", r: ["Sure, it's Li. L-I.", "好的，Li，L-I。"] },
            { h: "Booth or table?", z: "卡座还是普通桌？", r: ["A booth, please.", "卡座，谢谢。"] },
          ],
        },
        {
          title: "点饮料 / 点菜",
          items: [
            { h: "Can I get you started with something to drink?", z: "先给您来点喝的？", f: "Can I getcha started with somethin' to drink?", r: ["Just water, please.", "白水就好。"] },
            { h: "Still or sparkling?", z: "要普通水还是气泡水？", r: ["Still, please.", "普通水。"] },
            { h: "Are you ready to order?", z: "可以点菜了吗？", r: ["Can we have a few more minutes?", "能再给我们几分钟吗？"] },
            { s: "What do you recommend?", z: "你推荐什么？" },
            { s: "I'll have the chicken sandwich.", z: "我要鸡肉三明治。" },
            { s: "Can I get that without onions?", z: "能不放洋葱吗？" },
            { s: "Is it spicy?", z: "辣吗？" },
            { s: "I'm allergic to peanuts.", z: "我对花生过敏。" },
            { s: "Same for me, please.", z: "我也要一样的。" },
            { h: "How would you like your steak?", z: "牛排要几分熟？", r: ["Medium, please.", "五分熟。"] },
            { h: "Soup or salad?", z: "配汤还是沙拉？", r: ["Salad, please.", "沙拉。"] },
            { h: "What kind of dressing?", z: "要什么沙拉酱？", r: ["Ranch, please.", "田园酱。"] },
            { h: "That comes with fries. Is that okay?", z: "配薯条，可以吗？", r: ["Can I get a side salad instead?", "能换成小份沙拉吗？"] },
          ],
        },
        {
          title: "用餐中",
          items: [
            { h: "How is everything?", z: "吃得怎么样？", f: "How's ev'rything?", r: ["Great, thanks.", "很好，谢谢。"] },
            { h: "Can I get you anything else?", z: "还需要别的吗？", r: ["We're good, thanks.", "不用了，谢谢。"] },
            { h: "Are you still working on that?", z: "您还在吃吗？（问能不能收盘子）", r: ["Yes, I'm still working on it.", "还在吃。"] },
            { s: "Excuse me, could we get some napkins?", z: "打扰一下，能给点餐巾纸吗？" },
            { s: "Could I get a refill, please?", z: "能帮我续杯吗？" },
            { s: "Can I get a box?", z: "能给我个打包盒吗？" },
          ],
        },
        {
          title: "结账",
          items: [
            { s: "Can we get the check, please?", z: "麻烦买单。" },
            { h: "Is this all together or separate?", z: "一起付还是分开付？", r: ["Separate, please.", "分开付。"] },
            { s: "Can we split it?", z: "能分开付吗？" },
            { h: "I'll take that whenever you're ready.", z: "您准备好了我就来收。（放下账单时说）" },
            { h: "Do you need change?", z: "需要找零吗？（付现金时）", r: ["No, keep the change.", "不用找了。"] },
          ],
        },
        {
          title: "快餐 / 柜台点单",
          items: [
            { h: "For here or to go?", z: "堂食还是外带？", f: "For here or ta go?", r: ["To go, please.", "外带。"] },
            { h: "Do you want to make it a meal?", z: "要不要做成套餐？", r: ["Yes, a medium meal, please.", "要，中份套餐。"] },
            { h: "What size?", z: "要多大的？", r: ["Medium, please.", "中杯/中份。"] },
            { h: "Anything else for you?", z: "还要别的吗？", r: ["That's it.", "就这些。"] },
            { h: "Can I get a name for the order?", z: "订单留个名字？" },
            { h: "Number forty-two!", z: "42 号！（叫号取餐）" },
            { s: "Can I get a number three with a Coke?", z: "我要 3 号套餐，配可乐。" },
          ],
        },
      ],
    },

    // ------------------------------------------------------------
    {
      id: "ride",
      name: "打车",
      icon: "🚗",
      tip: "Uber/Lyft 上车前先核对车牌和司机名字，司机通常会问你的名字确认。坐后排更常见。小费可以下车后在 App 里给。找不到车时司机可能打电话或发短信。",
      dialogs: ["uber_ride"],
      sections: [
        {
          title: "上车确认",
          items: [
            { h: "Are you Li?", z: "你是 Li 吗？", r: ["Yes, that's me.", "是我。"] },
            { s: "Hi, are you David?", z: "你好，你是 David 吗？" },
            { h: "Can I get your name?", z: "你叫什么名字？（确认乘客）", r: ["It's Li.", "我叫 Li。"] },
            { s: "Could you open the trunk, please?", z: "能开一下后备箱吗？" },
            { h: "Do you need help with your bags?", z: "要帮你拿行李吗？", r: ["I'm good, thanks.", "不用了，谢谢。"] },
          ],
        },
        {
          title: "找不到车 / 接电话",
          items: [
            { h: "Hey, I'm here. Where are you?", z: "我到了，你在哪？" },
            { s: "I'm at the main entrance.", z: "我在正门。" },
            { s: "I'm wearing a black jacket.", z: "我穿着黑色外套。" },
            { s: "I'll be right out.", z: "我马上出来。" },
            { s: "Can you wait two minutes?", z: "能等我两分钟吗？" },
            { h: "I can't stop here. Can you come to the corner?", z: "这里不能停，你能到街角来吗？", r: ["Sure, I'm coming.", "好，我过去。"] },
            { h: "I'm in a white Honda.", z: "我开的是白色本田。" },
          ],
        },
        {
          title: "路上",
          items: [
            { h: "Where are you headed?", z: "你去哪？", f: "Where ya headed?", r: ["To the airport, please.", "去机场。"] },
            { h: "Which terminal?", z: "哪个航站楼？", r: ["Terminal B, please.", "B 航站楼。"] },
            { h: "Is the temperature okay back there?", z: "后面温度还行吗？", r: ["It's a little warm. Could you turn on the AC?", "有点热，能开下空调吗？"] },
            { h: "Any music you'd like?", z: "想听什么音乐吗？", r: ["Anything is fine.", "都行。"] },
            { h: "How's your day going?", z: "今天过得怎么样？（司机闲聊）", r: ["Pretty good, thanks. How about you?", "还不错，谢谢，你呢？"] },
          ],
        },
        {
          title: "下车",
          items: [
            { h: "Is here okay?", z: "在这里下可以吗？", r: ["Yes, right here is fine.", "可以，就这里。"] },
            { s: "Could you drop me off at the front door?", z: "能在正门放我下来吗？" },
            { s: "Can you pull over here?", z: "能在这里靠边停吗？" },
            { s: "Thanks, have a good one!", z: "谢谢，祝你愉快！" },
            { s: "Can I pay by card?", z: "可以刷卡吗？（出租车）" },
          ],
        },
      ],
    },

    // ------------------------------------------------------------
    {
      id: "transit",
      name: "公交地铁",
      icon: "🚌",
      tip: "公交车上要下车时，拉窗边的绳子或按 STOP 按钮，屏幕会显示 Stop requested。很多城市可以直接用信用卡或手机贴卡付车费。司机不开后门时可以喊 Back door, please!",
      dialogs: ["subway", "street_directions"],
      sections: [
        {
          title: "上车前问",
          items: [
            { s: "Does this bus go downtown?", z: "这辆车去市中心吗？" },
            { s: "Which bus goes to the mall?", z: "哪路车去商场？" },
            { s: "How much is the fare?", z: "车费多少钱？" },
            { s: "Can I tap my phone to pay?", z: "可以用手机贴一下付钱吗？" },
            { s: "How often does the bus come?", z: "这车多久来一班？" },
            { s: "Is this the right platform for the Red Line?", z: "这是红线的站台吗？" },
            { h: "You want the one going the other way.", z: "你要坐反方向的。", r: ["Oh, thank you!", "哦，谢谢！"] },
            { h: "You need to transfer at Union Station.", z: "你要在 Union Station 换乘。" },
            { h: "It's every fifteen minutes.", z: "每 15 分钟一班。" },
          ],
        },
        {
          title: "车上",
          items: [
            { s: "Could you tell me when we get to Main Street?", z: "到 Main Street 能告诉我一声吗？" },
            { s: "Where should I get off for the library?", z: "去图书馆在哪站下？" },
            { s: "Is this seat taken?", z: "这个座位有人吗？" },
            { h: "It's three stops from here.", z: "从这里还有三站。" },
            { h: "Please move to the back of the bus.", z: "请往车厢后面走。" },
            { h: "Next stop, Main Street.", z: "下一站，Main Street。（广播）" },
            { h: "Stop requested.", z: "已请求停车。（屏幕/广播）" },
            { h: "Stand clear of the closing doors, please.", z: "车门即将关闭，请勿靠近。（地铁广播）" },
            { h: "This bus is out of service.", z: "这辆车停止载客。" },
          ],
        },
        {
          title: "下车",
          items: [
            { s: "Excuse me, this is my stop.", z: "不好意思，我到站了。（请人让路）" },
            { s: "Back door, please!", z: "麻烦开一下后门！" },
            { s: "Excuse me, coming through.", z: "不好意思，借过。" },
          ],
        },
      ],
    },

    // ------------------------------------------------------------
    {
      id: "flight",
      name: "飞机",
      icon: "✈️",
      tip: "美国国内航班托运行李一般限重 50 磅（约 23kg），超重要加钱。过安检（TSA）常要拿出电脑，有时要脱鞋。登机按 Group 分组叫号，听到自己的组号再排队。",
      dialogs: ["domestic_flight", "airport"],
      sections: [
        {
          title: "值机 / 托运",
          items: [
            { h: "Where are you flying to today?", z: "今天飞哪里？", r: ["Chicago.", "芝加哥。"] },
            { h: "Can I see your ID, please?", z: "能看下你的证件吗？" },
            { h: "Are you checking any bags today?", z: "今天有行李要托运吗？", r: ["Yes, just one.", "有，就一件。"] },
            { h: "Go ahead and put your bag on the scale.", z: "把行李放到秤上吧。" },
            { h: "Your bag is a little overweight.", z: "你的行李有点超重。", r: ["How much over is it?", "超了多少？"] },
            { s: "Can I take this as a carry-on?", z: "这个可以随身带上飞机吗？" },
            { s: "Could I get an aisle seat?", z: "能给我靠过道的座位吗？" },
            { s: "Is the flight on time?", z: "航班准点吗？" },
          ],
        },
        {
          title: "安检 TSA",
          items: [
            { h: "Laptops out, liquids out.", z: "电脑拿出来，液体拿出来。" },
            { h: "Shoes off, belts off, everything out of your pockets.", z: "脱鞋，解皮带，口袋里的东西都拿出来。" },
            { h: "Step forward. Arms up.", z: "往前走，举起手。（扫描仪）" },
            { h: "Is this your bag? I need to take a look.", z: "这是你的包吗？我需要检查一下。", r: ["Yes, it's mine.", "是我的。"] },
            { s: "Do I need to take off my shoes?", z: "需要脱鞋吗？" },
          ],
        },
        {
          title: "登机口",
          items: [
            { s: "Is this the gate for Chicago?", z: "这是飞芝加哥的登机口吗？" },
            { s: "Has boarding started?", z: "开始登机了吗？" },
            { h: "We're now boarding group three.", z: "现在第 3 组登机。" },
            { h: "Flight 512 is delayed. The new departure time is 4:30.", z: "512 航班延误，新的起飞时间是 4:30。" },
            { h: "There's been a gate change. The flight will now depart from gate B12.", z: "登机口变更，现在改到 B12 登机口。" },
            { h: "This is the final boarding call for flight 512.", z: "512 航班最后登机广播。" },
          ],
        },
        {
          title: "飞机上",
          items: [
            { s: "Excuse me, I think you're in my seat.", z: "不好意思，你好像坐了我的位置。" },
            { s: "Is there any room in the overhead bin?", z: "头顶行李舱还有空间吗？" },
            { h: "Can I get you something to drink?", z: "要喝点什么吗？", r: ["Coffee, please. With cream, no sugar.", "咖啡，加奶不加糖。"] },
            { h: "Pretzels or cookies?", z: "要椒盐饼干还是曲奇？", r: ["Pretzels, please.", "椒盐饼干。"] },
            { h: "Please put that under the seat in front of you.", z: "请把它放到前排座位下面。" },
            { h: "Please make sure your seat is in the upright position.", z: "请把座椅靠背调直。" },
            { s: "Could I have a blanket, please?", z: "能给我一条毯子吗？" },
          ],
        },
        {
          title: "落地 / 行李 / 转机",
          items: [
            { s: "Where's baggage claim?", z: "行李提取处在哪？" },
            { s: "Where do I go for my connecting flight?", z: "转机往哪走？" },
            { s: "I missed my connection. What should I do?", z: "我误了转机，怎么办？" },
            { s: "My bag didn't come out.", z: "我的行李没出来。" },
            { h: "Can I see your baggage claim tag?", z: "能看下你的行李牌（托运凭条）吗？" },
            { h: "Can you describe your bag?", z: "能描述一下你的行李吗？", r: ["It's a black suitcase with a red tag.", "黑色行李箱，挂着红色标签。"] },
          ],
        },
      ],
    },

    // ------------------------------------------------------------
    {
      id: "package",
      name: "快递",
      icon: "📦",
      tip: "美国快递多数直接放门口，不用签收。没收到时：USPS 会留 “Sorry we missed you” 通知单，FedEx/UPS 留门贴，按上面的说明去取或改约。Amazon 退货可以拿到 UPS Store 等地，出示 App 里的二维码，常常不用包装。USPS 寄件时柜员一定会问一长串：有没有易碎、液体、易腐、危险品。",
      dialogs: [],
      sections: [
        {
          title: "收快递",
          items: [
            { h: "I have a package for you.", z: "有你的快递。" },
            { h: "Can you sign here, please?", z: "麻烦在这里签个字。" },
            { h: "Is this apartment 3B?", z: "这是 3B 公寓吗？", r: ["Yes, it is.", "是的。"] },
            { s: "Can you leave it at the door?", z: "能放门口吗？" },
            { s: "Could you leave it at the front desk?", z: "能放前台吗？" },
            { s: "Is there a package for me? My name is Li, apartment 3B.", z: "有我的快递吗？我叫 Li，3B 公寓。（问前台/物业）" },
          ],
        },
        {
          title: "取件（邮局 / 门店）",
          items: [
            { s: "I got this notice. I'd like to pick up my package.", z: "我收到这张通知单，想来取快递。" },
            { h: "Can I see your ID?", z: "能看下你的证件吗？" },
            { h: "What's the tracking number?", z: "单号是多少？", r: ["Here, it's on my phone.", "在我手机上，给你看。"] },
            { s: "Can I pick it up at the store instead?", z: "我能改成去店里取吗？" },
          ],
        },
        {
          title: "出问题了（客服 / 物业）",
          items: [
            { s: "My package says delivered, but I didn't get it.", z: "显示已送达，但我没收到。" },
            { s: "I think it was delivered to the wrong address.", z: "我觉得送错地址了。" },
            { s: "The box was damaged.", z: "箱子破损了。" },
            { s: "Something is missing from my order.", z: "我的订单少了东西。" },
            { s: "Can I reschedule the delivery?", z: "能改送货时间吗？" },
            { h: "Have you checked with your neighbors?", z: "你问过邻居了吗？" },
            { h: "We'll send a replacement.", z: "我们会给你补发。" },
            { h: "You'll get a full refund.", z: "会给你全额退款。" },
          ],
        },
        {
          title: "寄快递 / 退货",
          items: [
            { s: "I'd like to mail this package.", z: "我想寄这个包裹。" },
            { s: "How much is it to ship this to New York?", z: "寄到纽约多少钱？" },
            { s: "What's the cheapest way?", z: "最便宜的方式是哪种？" },
            { s: "How long will it take?", z: "要多久到？" },
            { s: "I need a box. Do you sell them?", z: "我需要一个箱子，你们卖吗？" },
            { s: "I have an Amazon return. Here's the QR code.", z: "我要退 Amazon 的货，这是二维码。" },
            { s: "Can I get a receipt with the tracking number?", z: "能给我带单号的收据吗？" },
            { h: "Is there anything fragile, liquid, perishable, or potentially hazardous?", z: "里面有易碎、液体、易腐或危险物品吗？", f: "Anything fragile-liquid-perishable-or-potentially-hazardous?（一口气说完）", r: ["No, it's just clothes.", "没有，只是衣服。"] },
            { h: "Priority or ground?", z: "要优先寄还是陆运（便宜慢）？", r: ["Ground is fine.", "陆运就行。"] },
            { h: "Do you want to add insurance?", z: "要加保险吗？", r: ["No, thanks.", "不用，谢谢。"] },
            { h: "It should get there in two to three business days.", z: "大概 2 到 3 个工作日到。" },
          ],
        },
      ],
    },
  ],
};
