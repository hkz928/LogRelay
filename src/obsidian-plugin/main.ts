import { Plugin } from "obsidian";
import { LogRelaySettings, DEFAULT_SETTINGS, LogRelaySettingTab } from "./settings";
import { RelayView, RELAY_VIEW_TYPE } from "./views/relay-view";
import { SearchView, SEARCH_VIEW_TYPE } from "./views/search-view";
import { StatsView, STATS_VIEW_TYPE } from "./views/stats-view";
import { LogParser } from "./services/log-parser";

export default class LogRelayPlugin extends Plugin {
	settings: LogRelaySettings;
	logParser: LogParser;

	async onload() {
		await this.loadSettings();

		this.logParser = new LogParser(this.app, this.settings);

		// 注册视图
		this.registerView(RELAY_VIEW_TYPE, (leaf) => new RelayView(leaf, this));
		this.registerView(SEARCH_VIEW_TYPE, (leaf) => new SearchView(leaf, this));
		this.registerView(STATS_VIEW_TYPE, (leaf) => new StatsView(leaf, this));

		// 侧边栏图标
		this.addRibbonIcon("git-branch", "LogRelay 接力链路", () => {
			this.activateView(RELAY_VIEW_TYPE);
		});
		this.addRibbonIcon("search", "LogRelay 日志搜索", () => {
			this.activateView(SEARCH_VIEW_TYPE);
		});
		this.addRibbonIcon("bar-chart-2", "LogRelay 统计", () => {
			this.activateView(STATS_VIEW_TYPE);
		});

		// 命令
		this.addCommand({
			id: "open-relay-view",
			name: "打开接力链路视图",
			callback: () => this.activateView(RELAY_VIEW_TYPE),
		});
		this.addCommand({
			id: "open-search-view",
			name: "打开日志搜索",
			callback: () => this.activateView(SEARCH_VIEW_TYPE),
		});
		this.addCommand({
			id: "open-stats-view",
			name: "打开统计面板",
			callback: () => this.activateView(STATS_VIEW_TYPE),
		});
		this.addCommand({
			id: "refresh-index",
			name: "刷新搜索索引",
			callback: () => {
				this.logParser.refreshIndex();
				new Notice("LogRelay 索引已刷新");
			},
		});

		// 设置页
		this.addSettingTab(new LogRelaySettingTab(this.app, this));

		// 定时刷新索引
		this.registerInterval(
			window.setInterval(
				() => this.logParser.refreshIndex(),
				this.settings.searchIndexInterval * 60 * 1000
			)
		);
	}

	onunload() {}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}

	async activateView(viewType: string) {
		const existing = this.app.workspace.getLeavesOfType(viewType);
		if (existing.length > 0) {
			this.app.workspace.revealLeaf(existing[0]);
			return;
		}
		const leaf = this.app.workspace.getRightLeaf(false);
		if (leaf) {
			await leaf.setViewState({ type: viewType, active: true });
			this.app.workspace.revealLeaf(leaf);
		}
	}
}
