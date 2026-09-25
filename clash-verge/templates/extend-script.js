// Clash Verge Extend Script Template (parko profile)
// 位置：profiles/saDMY9wRANlr.js（通过 Clash Verge GUI → parko → script 绑定）
// ============================================================================
// 此模板由 clash-verge skill 维护。修改后需在 Clash Verge 中刷新 parko profile 生效。
// ============================================================================

function main(config) {
  // 1. 全局底层网络优化 (TCP保活)
  config["tcp-concurrent"] = true;
  config["keep-alive-interval"] = 15;
  config["keep-alive-idle"] = 30;

  // 2. DNS 优化：解决公司内网域名解析问题
  if (!config.dns) config.dns = {};
  if (!config.dns["nameserver-policy"]) config.dns["nameserver-policy"] = {};

  // 统一 DNS 源：多接口并发查询
  // - en0/en1 覆盖不同 Mac 主网卡（办公机主接口可能是 en0 或 en1）
  // - mihomo 并发向所有源查询，无租约接口静默失败
  //
  // 小米办公网透明代理机制（2026-07-05 实测）：
  //   拦截所有 UDP:53 DNS 查询返回真实 IP（不污染），TCP 443 直连真实 IP 可达
  //   → 内网域名(*.mioffice.cn 等) 和被墙域名(youtube/x.com/telegram/github)
  //     都能通过 dhcp://enN 拿到真实 IP，走 DIRECT 比走代理快 3-4 倍
  //   → mihomo 内部 DNS 绕过系统透明拦截，但 dhcp://enN 直连小米 DNS 仍被拦截
  //
  // ⚠️ 裸 IP 有效性复盘（2026-07-06 修正）：
  //   - 2026-06-03 记录"裸 IP 是 TUN 模式下唯一可靠格式"
  //   - 2026-07-05 误判"裸 IP 无效已回滚"——当时没实测，是基于"被墙域名需要 dhcp://en1
  //     享受透明代理"的错误外推。实际内网域名用裸 IP 5/5 成功（2026-07-06 实测）
  //   - 真相：mihomo 内部 DNS 查询不被自己的 TUN dns-hijack 拦截，裸 IP 直连小米 DNS
  //     可成功；外部进程（dig/curl）的 UDP:53 才会被 TUN 拦截
  //   - 被 git@dig @10.234.253.8 拿到 fake-ip 是因为 dig 是外部进程，不是裸 IP 无效
  //
  // ⚠️ 内网域名 vs 被墙域名的 DNS 源（2026-07-06 修正：可统一）：
  //   之前认为被墙域名不能加裸 IP/system 是错的（基于推理没实测）。
  //   实测发现：小米办公网透明代理拦截所有 UDP:53 查询返回真实 IP（不污染），
  //   mihomo 内部 DNS 发到 10.234.253.8:53 的查询也被透明代理拦截拿到真实 IP。
  //   - youtube 走裸 IP 5/5 拿到 Google 真实 IP 142.250.204.46（非 GFW 污染 IP）
  //   - 之前 youtube 加 system 拿到 Twitter IP 104.244.42.197 的根因是：
  //     system 走 mihomo 内部 resolver 时可能并发查询产生竞态，但加裸 IP 后
  //     裸 IP 抢跑返回真实 IP，system 即使污染也来不及抢赢
  //   结论：blockedDNS 可以跟 officeDNS 统一，都用全量源
  const officeDNS = ["10.234.253.8", "10.234.254.8", "dhcp://en0", "dhcp://en1", "system"];  // 内网域名
  const blockedDNS = ["10.234.253.8", "10.234.254.8", "dhcp://en0", "dhcp://en1"];            // 被墙域名（不加 system）
  // 注：blockedDNS 不加 system 是保守起见——内网域名加 system 无害（不被污染），
  // 被墙域名加 system 万一裸 IP 失败时 system 可能抢跑返回污染 IP。
  // 裸 IP + dhcp:// 已经足够稳定，没必要冒这个险。

  // default-nameserver：mihomo 启动时的 bootstrap DNS（不经过 TUN hijack）
  // 用于解析 dhcp://en1 等 scheme 需要先查 DHCP 服务器地址的场景
  config.dns["default-nameserver"] = ["10.234.253.8", "10.234.254.8"];

  // 内网域名
  config.dns["nameserver-policy"]["+.mioffice.cn"] = officeDNS;
  config.dns["nameserver-policy"]["+.mi.srv"] = officeDNS;
  config.dns["nameserver-policy"]["+.alb.xiaomi.srv"] = officeDNS; // CNAME 终点（小米内网 ALB，如 intranet-staging-xxx.alb.xiaomi.srv）
  config.dns["nameserver-policy"]["+.xiaomi.srv"] = officeDNS;
  config.dns["nameserver-policy"]["+.xiaomi.com"] = officeDNS;
  config.dns["nameserver-policy"]["+.xiaomi.net"] = officeDNS;
  config.dns["nameserver-policy"]["+.mi.com"] = officeDNS;
  config.dns["nameserver-policy"]["+.olap.srv"] = officeDNS;
  config.dns["nameserver-policy"]["+.mi-dun.com"] = officeDNS;
  config.dns["nameserver-policy"]["+.mi-dun.srv"] = officeDNS; // CNAME 终点（如 cname-app-com.n.mi-dun.srv）
  config.dns["nameserver-policy"]["+.mitvos.com"] = officeDNS;
  config.dns["nameserver-policy"]["+.apple-cloudkit.com"] = officeDNS;
  config.dns["nameserver-policy"]["+.icloud.com"] = officeDNS;
  config.dns["nameserver-policy"]["+.icloud-content.com"] = officeDNS;
  config.dns["nameserver-policy"]["+.multica.ai"] = officeDNS;
  config.dns["nameserver-policy"]["+.typeless-static.com"] = officeDNS;

  // 被墙域名走 DIRECT（办公网透明代理可达，省代理流量，速度快 3-4 倍）
  // 注意：google/anthropic/claude.ai 虽可达，但用户选择走 PROXY（见 rules override）
  config.dns["nameserver-policy"]["+.youtube.com"] = blockedDNS;
  config.dns["nameserver-policy"]["+.x.com"] = blockedDNS;
  config.dns["nameserver-policy"]["+.t.me"] = blockedDNS;
  config.dns["nameserver-policy"]["+.telegram.org"] = blockedDNS;
  config.dns["nameserver-policy"]["+.githubusercontent.com"] = blockedDNS;
  config.dns["nameserver-policy"]["+.github.io"] = blockedDNS;
  config.dns["nameserver-policy"]["+.kiro.dev"] = blockedDNS;


  // Avoid Xiaomi 198.18.0.0/16 conflict by switching fake-ip range
  config.dns["fake-ip-range"] = "28.0.0.1/16";

  // 避免 fake-ip 导致内网解析混乱，将内网域名加入 fake-ip-filter
  // ⚠️ 必须用 +. 语法，不能用 *. ：
  //   - *.xiaomi.com 只匹配 foo.xiaomi.com（单级子域），不匹配 ds.ad.xiaomi.com（多级子域）
  //   - +.xiaomi.com 匹配 xiaomi.com + 所有子域（包括多级）
  //   用 *. 会导致多级子域走 fake-ip，浏览器拿 fake-ip 后 mihomo 反查映射，
  //   flush fakeip 缓存后映射丢失 → 连接被拒 → "时好时坏"
  if (!config.dns["fake-ip-filter"]) config.dns["fake-ip-filter"] = [];
  const intranetFilters = ["+.mioffice.cn", "+.mi.srv", "+.alb.xiaomi.srv", "+.xiaomi.srv", "+.xiaomi.com", "+.xiaomi.net", "+.mi.com", "+.olap.srv", "+.mi-dun.com", "+.mi-dun.srv", "+.mitvos.com", "+.apple-cloudkit.com", "+.icloud.com", "+.icloud-content.com", "+.multica.ai", "+.typeless-static.com"];
  intranetFilters.forEach(filter => {
    if (!config.dns["fake-ip-filter"].includes(filter)) {
      config.dns["fake-ip-filter"].push(filter);
    }
  });

  if (!config.proxies || !Array.isArray(config.proxies)) return config;

  // 3. 模糊匹配寻找节点（彻底解决名字带国旗emoji或隐藏空格导致找不到的BUG）
  const exitProxy = config.proxies.find(p => p.name.includes("圣何塞静态ip2"));
  const entryProxy = config.proxies.find(p => p.name.includes("parko-tokyo")); // 只用核心词搜索，避开emoji

  // 只有当两个节点都成功找到时，才进行组装，防止报错瘫痪
  if (exitProxy && entryProxy) {
    // 4. 克隆并组装链式节点
    let chainedProxy = JSON.parse(JSON.stringify(exitProxy));
    chainedProxy.name = "圣何塞-链式出口";
    chainedProxy["dialer-proxy"] = entryProxy.name; // 直接提取系统里真实准确的名字
    config.proxies.push(chainedProxy);

    // 5. 套上心跳保活组
    const keepAliveGroup = {
      "name": "🛡️ 圣何塞-终极保活链",
      "type": "url-test",
      "url": "http://www.gstatic.com/generate_204",
      "interval": 100,
      "tolerance": 300,
      "proxies": ["圣何塞-链式出口"]
    };

    if (!config["proxy-groups"]) config["proxy-groups"] = [];
    config["proxy-groups"].unshift(keepAliveGroup);

    // 6. 将该组强行插入到所有的节点选择列表中
    config["proxy-groups"].forEach(group => {
      if (group.type === "select") {
        group.proxies.unshift("🛡️ 圣何塞-终极保活链");
      }
    });
  }

  return config;
}
