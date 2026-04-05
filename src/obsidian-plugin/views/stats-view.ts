import { ItemView, WorkspaceLeaf } from "obsidian";
import LogRelayPlugin from "../main";

export const STATS_VIEW_TYPE = "logrelay-stats-view";

export class StatsView extends ItemView {
	plugin: LogRelayPlugin;

	constructor(leaf: WorkspaceLeaf, plugin: LogRelayPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string {
		return STATS_VIEW_TYPE;
	}

	getDisplayText(): string {
		return "LogRelay 统计";
	}

	getIcon(): string {
		return "bar-chart-2";
	}

	async onOpen() {
		const container = this.containerEl.children[1] as HTMLElement;
		container.empty();
		container.classList.add("logrelay-stats-view");

		await this.plugin.logParser.refreshIndex();
		this.render(container);
	}

	private render(container: HTMLElement) {
		container.empty();

		const stats = this.plugin.logParser.getStats(this.plugin.settings.statsPeriodDays);

		// 标题
		const header = container.createDiv({ cls: "logrelay-header" });
		header.createEl("h3", { text: `LogRelay 统计（近 ${this.plugin.settings.statsPeriodDays} 天）` });

		// 工具使用频率
		const toolSection = container.createDiv({ cls: "logrelay-stats-section" });
		toolSection.createEl("h4", { text: "工具使用频率" });
		const maxCount = Math.max(...stats.toolFrequency.map(([, c]) => c), 1);

		for (const [tool, count] of stats.toolFrequency) {
			const row = toolSection.createDiv({ cls: "logrelay-stats-bar-row" });
			row.createSpan({ text: tool, cls: "logrelay-stats-bar-label" });
			const barContainer = row.createDiv({ cls: "logrelay-stats-bar-container" });
			const bar = barContainer.createDiv({ cls: "logrelay-stats-bar" });
			const pct = Math.round((count / maxCount) * 100);
			bar.style.width = `${pct}%`;
			bar.setAttribute("data-count", String(count));
			row.createSpan({ text: `${Math.round((count / stats.totalSessions) * 100)}%`, cls: "logrelay-stats-bar-pct" });
		}

		// 任务完成率
		const taskSection = container.createDiv({ cls: "logrelay-stats-section" });
		taskSection.createEl("h4", { text: "任务完成率" });

		const taskSummary = taskSection.createDiv({ cls: "logrelay-task-summary" });
		taskSummary.createEl("div", { text: `总任务: ${stats.totalTasks}` });
		taskSummary.createEl("div", { text: `已完成: ${stats.completedTasks} (${stats.totalTasks > 0 ? Math.round((stats.completedTasks / stats.totalTasks) * 100) : 0}%)` });
		taskSummary.createEl("div", { text: `进行中: ${stats.pendingTasks}` });

		// 任务进度条
		if (stats.totalTasks > 0) {
			const progressBar = taskSection.createDiv({ cls: "logrelay-progress-bar" });
			const progressFill = progressBar.createDiv({ cls: "logrelay-progress-fill" });
			progressFill.style.width = `${(stats.completedTasks / stats.totalTasks) * 100}%`;
		}

		// 活跃度热力图
		const heatmapSection = container.createDiv({ cls: "logrelay-stats-section" });
		heatmapSection.createEl("h4", { text: "活跃度" });

		const heatmapGrid = heatmapSection.createDiv({ cls: "logrelay-heatmap" });
		const today = new Date();
		const maxActivity = Math.max(...Array.from(stats.dailyActivity.values()), 1);

		for (let i = 29; i >= 0; i--) {
			const date = new Date(today);
			date.setDate(date.getDate() - i);
			const dateStr = date.toISOString().slice(0, 10);
			const count = stats.dailyActivity.get(dateStr) || 0;

			const cell = heatmapGrid.createDiv({ cls: "logrelay-heatmap-cell" });
			const intensity = count > 0 ? Math.ceil((count / maxActivity) * 4) : 0;
			cell.classList.add(`logrelay-heat-${intensity}`);
			cell.setAttribute("title", `${dateStr}: ${count} 会话`);
		}

		// 项目活跃度 TOP 5
		if (stats.topProjects.length > 0) {
			const projectSection = container.createDiv({ cls: "logrelay-stats-section" });
			projectSection.createEl("h4", { text: "项目活跃度 TOP 5" });

			const list = projectSection.createEl("ol", { cls: "logrelay-top-projects" });
			for (const [name, count] of stats.topProjects) {
				const li = list.createEl("li");
				li.createSpan({ text: `${name} ` });
				li.createSpan({ text: `(${count} 会话)`, cls: "logrelay-stats-count" });
			}
		}
	}

	async onClose() {}
}
