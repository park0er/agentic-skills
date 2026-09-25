import { execSync } from "child_process";

const REGISTRY = "https://pkgs.d.xiaomi.net/artifactory/api/npm/npm-snapshot-local/";
const PACKAGE = "@mimocode/cli-ai";

function getLocalVersion(mimoBin: string): string {
  try {
    const output = execSync(`"${mimoBin}" --version`, { stdio: "pipe", timeout: 5000 });
    return output.toString().trim().replace(/^v/, "");
  } catch {
    return "";
  }
}

function getRemoteVersion(): string {
  try {
    const output = execSync(`npm view ${PACKAGE} version --registry=${REGISTRY}`, {
      stdio: "pipe",
      timeout: 15000,
    });
    return output.toString().trim().replace(/^v/, "");
  } catch {
    return "";
  }
}

function installMimoCode(): boolean {
  try {
    execSync(`npm install -g ${PACKAGE} --registry=${REGISTRY}`, { stdio: "inherit" });
    return true;
  } catch {
    return false;
  }
}

export function ensureMimoCodeUpdated(mimoBin: string): void {
  const localVersion = getLocalVersion(mimoBin);
  const remoteVersion = getRemoteVersion();

  if (!localVersion) {
    console.log("📦 未检测到 mimocode，正在安装...");
    if (installMimoCode()) {
      const newVer = getLocalVersion(mimoBin) || remoteVersion;
      console.log(`✅ mimocode 安装成功 (v${newVer})`);
    } else {
      console.error("❌ mimocode 安装失败");
      console.error(`   请手动安装: npm install -g ${PACKAGE} --registry=${REGISTRY}`);
      process.exit(1);
    }
    return;
  }

  if (!remoteVersion) {
    return;
  }

  if (localVersion !== remoteVersion) {
    console.log(`🔄 检测到 mimocode 新版本 (本地 v${localVersion} → 最新 v${remoteVersion})，正在更新...`);
    if (installMimoCode()) {
      console.log(`✅ mimocode 已更新到 v${remoteVersion}`);
    } else {
      console.warn("⚠️ mimocode 更新失败，继续使用当前版本");
    }
  }
}
