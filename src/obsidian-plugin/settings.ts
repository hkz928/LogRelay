import { App, PluginSettingTab, Setting } from "obsidian";
import LogRelayPlugin from "./main";

export interface LogRelaySettings {
	logsDirName: string;
	statusFileName: string;
	relayDisplayDepth: number;
	searchIndexInterval: number;
	statsPeriodDays: number;
}

export const DEFAULT_SETTINGS: LogRelaySettings = {
	logsDirName: "logs",
	statusFileName: "STATUS.md",
	relayDisplayDepth: 10,
	searchIndexInterval: 5,
	statsPeriodDays: 30,
};

export class LogRelaySettingTab extends PluginSettingTab {
	plugin: LogRelayPlugin;

	constructor(app: App, plugin: LogRelayPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		containerEl.createEl("h2", { text: "LogRelay 设置" });

		new Setting(containerEl)
			.setName("日志目录名")
			.setDesc("项目下存储日志的目录名")
			.addText((text) =>
				text
					.setPlaceholder("logs")
					.setValue(this.plugin.settings.logsDirName)
					.onChange(async (value) => {
						this.plugin.settings.logsDirName = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("状态文件名")
			.setDesc("跨工具接力状态文件名")
			.addText((text) =>
				text
					.setPlaceholder("STATUS.md")
					.setValue(this.plugin.settings.statusFileName)
					.onChange(async (value) => {
						this.plugin.settings.statusFileName = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("接力链路：显示深度")
			.setDesc("最多显示几层接力关系")
			.addSlider((slider) =>
				slider
					.setLimits(1, 50, 1)
					.setValue(this.plugin.settings.relayDisplayDepth)
					.setDynamicTooltip()
					.onChange(async (value) => {
						this.plugin.settings.relayDisplayDepth = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("搜索：索引间隔（分钟）")
			.setDesc("搜索索引自动刷新频率")
			.addSlider((slider) =>
				slider
					.setLimits(1, 60, 1)
					.setValue(this.plugin.settings.searchIndexInterval)
					.setDynamicTooltip()
					.onChange(async (value) => {
						this.plugin.settings.searchIndexInterval = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("统计：统计周期（天）")
			.setDesc("统计面板默认时间范围")
			.addSlider((slider) =>
				slider
					.setLimits(7, 365, 1)
					.setValue(this.plugin.settings.statsPeriodDays)
					.setDynamicTooltip()
					.onChange(async (value) => {
						this.plugin.settings.statsPeriodDays = value;
						await this.plugin.saveSettings();
					})
			);
	}
}
