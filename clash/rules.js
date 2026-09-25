// Clash Verge 脚本覆写（script 层）
//
// 这个文件里是「必须排在订阅自带规则之前」的分流修正。
// 逻辑：先把自己写的规则从 config.rules 里删掉（幂等，重复执行不会累积），
// 再 unshift 到最前面，所以订阅更新后依然生效。
//
// 维护时只改下面的数组，不用动 main() 的框架代码。

function main(config, profileName) {
  if (!Array.isArray(config.rules)) {
    config.rules = [];
  }

  // 优先排在最前的规则，按数组顺序生效。
  const prependRules = [
    // ── Steam ───────────────────────────────────────────────────
    // 住宅代理出口对这两个 SNI 会直接重置 TLS（同一节点上 store / login /
    // community 都正常），Steam 因此取不到 CM 列表，一直卡在重连循环。
    // 两者直连实测可用，所以必须排在下面的 steampowered.com PROXY 之前。
    "DOMAIN,api.steampowered.com,DIRECT",
    "DOMAIN,checkout.steampowered.com,DIRECT",
    // 其余 Steam 域名保持走代理：community 在国内直连不通，
    // 因此必须排在订阅的 category-games@cn DIRECT 规则之前。
    "DOMAIN-SUFFIX,steampowered.com,PROXY",
    "DOMAIN-SUFFIX,steamcommunity.com,PROXY",
    "DOMAIN-SUFFIX,steamstatic.com,PROXY",
    "DOMAIN-SUFFIX,steamserver.net,PROXY",
    "DOMAIN-SUFFIX,steamcontent.com,PROXY",
    "DOMAIN-SUFFIX,steamusercontent.com,PROXY",
    "DOMAIN-SUFFIX,steam-chat.com,PROXY",
    "DOMAIN-SUFFIX,steamgames.com,PROXY",
    "DOMAIN-SUFFIX,steam.tv,PROXY",
    "DOMAIN-SUFFIX,steamcdn-a.akamaihd.net,PROXY",
    "DOMAIN-SUFFIX,steamstore-a.akamaihd.net,PROXY",

    // ── Epic / hCaptcha ─────────────────────────────────────────
    // Epic 认证与 hCaptcha 必须走同一条直连路径；分开走会让 CAPTCHA
    // 无法初始化。
    "DOMAIN-SUFFIX,epicgames.com,DIRECT",
    "DOMAIN-SUFFIX,epicgames.dev,DIRECT",
    "DOMAIN-SUFFIX,unrealengine.com,DIRECT",
    "DOMAIN-SUFFIX,hcaptcha.com,DIRECT",
    "DOMAIN-SUFFIX,featureassets.org,DIRECT",
    "DOMAIN-SUFFIX,prodregistryv2.org,DIRECT",

    // ── WorkBuddy / CodeBuddy ───────────────────────────────────
    // 登录页、遥测、插件市场走代理会超时，仅这些产品域名直连。
    // 不要用宽泛的 Electron 进程规则，会误伤其他 Electron 应用。
    "DOMAIN-SUFFIX,workbuddy.ai,DIRECT",
    "DOMAIN-SUFFIX,workbuddy.cn,DIRECT",
    "DOMAIN-SUFFIX,codebuddy.ai,DIRECT",
    "DOMAIN-SUFFIX,tgalileo.com,DIRECT",
    "DOMAIN-SUFFIX,cnb.cool,DIRECT",

    // ── 百度网盘 ────────────────────────────────────────────────
    // 登录壳依赖 pan.baidu.com；直连超时、代理可达，只覆盖这一个主机。
    "DOMAIN,pan.baidu.com,PROXY",
  ];

  // 进程级规则：只在这些客户端有效（桌面端）。手机端会忽略。
  const processRules = [
    // KamaGames Texas Poker 用私有协议连裸 IP 游戏服务器，
    // 走住宅代理会断，整个进程直连。
    "PROCESS-NAME,Texas Poker,DIRECT",
  ];

  const allRules = [...prependRules, ...processRules];
  config.rules = config.rules.filter((rule) => !allRules.includes(rule));
  config.rules.unshift(...allRules);

  return config;
}
