import { ItemView, WorkspaceLeaf } from "obsidian";
import LogRelayPlugin from "../main";
import { SearchFilters, LogEntry } from "../services/log-parser";

export const SEARCH_VIEW_TYPE = "logrelay-search-view";

export class SearchView extends ItemView {
	plugin: LogRelayPlugin;
	private currentQuery: string = "";
	private filters: SearchFilters = {};
	private resultCount: number = 0;

	constructor(leaf: WorkspaceLeaf, plugin: LogRelayPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string {
		return SEARCH_VIEW_TYPE;
	}

	getDisplayText(): string {
		return "LogRelay 日志搜索";
	}

	getIcon(): string {
		return "search";
	}

	async onOpen() {
		const container = this.containerEl.children[1] as HTMLElement;
		container.empty();
		container.classList.add("logrelay-search-view");

		await this.plugin.logParser.refreshIndex();
		this.render(container);
	}

	private render(container: HTMLElement) {
		container.empty();

		// 标题
		const header = container.createDiv({ cls: "logrelay-header" });
		header.createEl("h3", { text: "日志搜索" });

		// 搜索框
		const searchBar = container.createDiv({ cls: "logrelay-search-bar" });
		const input = searchBar.createEl("input", {
			type: "text",
			placeholder: "搜索日志内容...",
			cls: "logrelay-search-input",
		});
		input.value = this.currentQuery;

		// 筛选器
		const filterBar = container.createDiv({ cls: "logrelay-filter-bar" });

		const tools = this.plugin.logParser.getAllTools();
		const projects = this.plugin.logParser.getAllProjects();

		const toolSelect = filterBar.createEl("select", { cls: "logrelay-filter" });
		toolSelect.createEl("option", { text: "工具: 全部", value: "" });
		for (const t of tools) {
			toolSelect.createEl("option", { text: t, value: t });
		}
		toolSelect.value = this.filters.tool || "";

		const projectSelect = filterBar.createEl("select", { cls: "logrelay-filter" });
		projectSelect.createEl("option", { text: "项目: 全部", value: "" });
		for (const p of projects) {
			projectSelect.createEl("option", { text: p, value: p });
		}
		projectSelect.value = this.filters.project || "";

		const statusSelect = filterBar.createEl("select", { cls: "logrelay-filter" });
		statusSelect.createEl("option", { text: "状态: 全部", value: "" });
		for (const s of ["active", "completed", "paused", "failed"]) {
			statusSelect.createEl("option", { text: s, value: s });
		}
		statusSelect.value = this.filters.status || "";

		const dateSelect = filterBar.createEl("select", { cls: "logrelay-filter" });
		dateSelect.createEl("option", { text: "近7天", value: "7" });
		dateSelect.createEl("option", { text: "近30天", value: "30", attr: { selected: "" } });
		dateSelect.createEl("option", { text: "近90天", value: "90" });
		dateSelect.createEl("option", { text: "全部", value: "0" });

		// 结果区域
		const resultsContainer = container.createDiv({ cls: "logrelay-search-results" });

		const doSearch = () => {
			this.currentQuery = input.value;
			this.filters = {
				tool: toolSelect.value || undefined,
				project: projectSelect.value || undefined,
				status: statusSelect.value || undefined,
			};

			const days = parseInt(dateSelect.value);
			if (days > 0) {
				const cutoff = new Date();
				cutoff.setDate(cutoff.getDate() - days);
				this.filters.dateFrom = cutoff.toISOString().slice(0, 10);
			}

			const results = this.plugin.logParser.searchLogs(this.currentQuery, this.filters);
			this.renderResults(resultsContainer, results);
		};

		input.addEventListener("input", doSearch);
		toolSelect.addEventListener("change", doSearch);
		projectSelect.addEventListener("change", doSearch);
		statusSelect.addEventListener("change", doSearch);
		dateSelect.addEventListener("change", doSearch);

		// 初始搜索
		doSearch();
	}

	private renderResults(container: HTMLElement, results: LogEntry[]) {
		container.empty();

		const countEl = container.createDiv({ cls: "logrelay-result-count" });
		countEl.setText(`结果 (${results.length} 条)`);

		if (results.length === 0) {
			container.createEl("p", { text: "未找到匹配的日志。", cls: "logrelay-empty" });
			return;
		}

		for (const entry of results) {
			const card = container.createDiv({ cls: "logrelay-result-card" });
			card.addEventListener("click", () => {
				this.app.workspace.getLeaf(false).openFile(entry.file);
			});

			const title = card.createDiv({ cls: "logrelay-result-title" });
			title.setText(entry.summary.slice(0, 60) || entry.frontmatter.session_id);

			const meta = card.createDiv({ cls: "logrelay-result-meta" });
			const date = entry.frontmatter.started.slice(0, 10);
			meta.createSpan({ text: entry.frontmatter.tool });
			meta.createSpan({ text: " | " });
			meta.createSpan({ text: entry.frontmatter.project });
			meta.createSpan({ text: " | " });
			meta.createSpan({ text: date });

			if (entry.frontmatter.tags && entry.frontmatter.tags.length > 0) {
				const tags = card.createDiv({ cls: "logrelay-result-tags" });
				for (const tag of entry.frontmatter.tags) {
					tags.createSpan({ text: `#${tag}`, cls: "logrelay-tag" });
				}
			}
		}
	}

	async onClose() {}
}
