import { App, TFile, TFolder, TAbstractFile, MetadataCache, Vault } from "obsidian";
import { LogRelaySettings } from "../settings";

export interface FrontmatterData {
	tool: string;
	tool_version: string;
	session_id: string;
	project: string;
	project_path: string;
	started: string;
	ended: string | null;
	status: string;
	tags: string[];
	handoff_to: string | null;
}

export interface LogEntry {
	file: TFile;
	frontmatter: FrontmatterData;
	summary: string;
	tasks: TaskItem[];
	decisions: string[];
	artifacts: string[];
	context: {
		depends_on: string | null;
		related_files: string | null;
	};
}

export interface TaskItem {
	text: string;
	completed: boolean;
}

export interface RelayNode {
	sessionId: string;
	tool: string;
	project: string;
	started: string;
	status: string;
	summary: string;
	file: TFile;
	dependsOn: string | null;
	children: RelayNode[];
}

export class LogParser {
	app: App;
	settings: LogRelaySettings;
	private index: LogEntry[] = [];
	private lastRefresh: number = 0;

	constructor(app: App, settings: LogRelaySettings) {
		this.app = app;
		this.settings = settings;
	}

	async refreshIndex(): Promise<void> {
		const entries: LogEntry[] = [];
		const logDirs = this.findLogDirectories();

		for (const dir of logDirs) {
			const files = this.getLogFiles(dir);
			for (const file of files) {
				const entry = await this.parseLogFile(file);
				if (entry) {
					entries.push(entry);
				}
			}
		}

		this.index = entries;
		this.lastRefresh = Date.now();
	}

	getAllLogs(): LogEntry[] {
		return this.index;
	}

	getLogsByProject(project: string): LogEntry[] {
		return this.index.filter((e) => e.frontmatter.project === project);
	}

	getLogsByTool(tool: string): LogEntry[] {
		return this.index.filter((e) => e.frontmatter.tool === tool);
	}

	searchLogs(query: string, filters?: SearchFilters): LogEntry[] {
		let results = this.index;
		const q = query.toLowerCase();

		if (filters) {
			if (filters.tool) results = results.filter((e) => e.frontmatter.tool === filters.tool);
			if (filters.project) results = results.filter((e) => e.frontmatter.project === filters.project);
			if (filters.status) results = results.filter((e) => e.frontmatter.status === filters.status);
			if (filters.dateFrom) results = results.filter((e) => e.frontmatter.started >= filters.dateFrom!);
			if (filters.dateTo) results = results.filter((e) => e.frontmatter.started <= filters.dateTo!);
			if (filters.tags && filters.tags.length > 0) {
				results = results.filter((e) =>
					filters.tags!.some((t) => e.frontmatter.tags?.includes(t))
				);
			}
		}

		if (q) {
			results = results.filter((e) => {
				const fm = e.frontmatter;
				return (
					e.summary.toLowerCase().includes(q) ||
					fm.project.toLowerCase().includes(q) ||
					fm.session_id.toLowerCase().includes(q) ||
					e.tasks.some((t) => t.text.toLowerCase().includes(q)) ||
					e.decisions.some((d) => d.toLowerCase().includes(q)) ||
					(fm.tags || []).some((t) => t.toLowerCase().includes(q))
				);
			});
		}

		return results.sort((a, b) => b.frontmatter.started.localeCompare(a.frontmatter.started));
	}

	buildRelayGraph(project: string): RelayNode[] {
		const logs = this.getLogsByProject(project);
		const nodeMap = new Map<string, RelayNode>();
		const roots: RelayNode[] = [];

		for (const log of logs) {
			const node: RelayNode = {
				sessionId: log.frontmatter.session_id,
				tool: log.frontmatter.tool,
				project: log.frontmatter.project,
				started: log.frontmatter.started,
				status: log.frontmatter.status,
				summary: log.summary.slice(0, 50),
				file: log.file,
				dependsOn: log.context.depends_on,
				children: [],
			};
			nodeMap.set(log.frontmatter.session_id, node);
		}

		for (const node of nodeMap.values()) {
			if (node.dependsOn) {
				const parent = nodeMap.get(node.dependsOn);
				if (parent) {
					parent.children.push(node);
				} else {
					roots.push(node);
				}
			} else {
				roots.push(node);
			}
		}

		return roots.sort((a, b) => a.started.localeCompare(b.started));
	}

	getAllProjects(): string[] {
		const projects = new Set(this.index.map((e) => e.frontmatter.project));
		return Array.from(projects).sort();
	}

	getAllTools(): string[] {
		const tools = new Set(this.index.map((e) => e.frontmatter.tool));
		return Array.from(tools).sort();
	}

	getAllTags(): string[] {
		const tags = new Set<string>();
		for (const e of this.index) {
			if (e.frontmatter.tags) {
				e.frontmatter.tags.forEach((t) => tags.add(t));
			}
		}
		return Array.from(tags).sort();
	}

	getStats(periodDays: number): StatsData {
		const cutoff = new Date();
		cutoff.setDate(cutoff.getDate() - periodDays);
		const cutoffStr = cutoff.toISOString().slice(0, 10);

		const recentLogs = this.index.filter((e) => e.frontmatter.started >= cutoffStr);

		// 工具使用频率
		const toolCounts = new Map<string, number>();
		for (const log of recentLogs) {
			toolCounts.set(log.frontmatter.tool, (toolCounts.get(log.frontmatter.tool) || 0) + 1);
		}
		const totalSessions = recentLogs.length;

		// 任务完成率
		let totalTasks = 0;
		let completedTasks = 0;
		for (const log of recentLogs) {
			for (const task of log.tasks) {
				totalTasks++;
				if (task.completed) completedTasks++;
			}
		}

		// 活跃度热力图（按天统计）
		const dailyActivity = new Map<string, number>();
		for (const log of recentLogs) {
			const day = log.frontmatter.started.slice(0, 10);
			dailyActivity.set(day, (dailyActivity.get(day) || 0) + 1);
		}

		// 项目活跃度
		const projectCounts = new Map<string, number>();
		for (const log of recentLogs) {
			projectCounts.set(log.frontmatter.project, (projectCounts.get(log.frontmatter.project) || 0) + 1);
		}
		const topProjects = Array.from(projectCounts.entries())
			.sort((a, b) => b[1] - a[1])
			.slice(0, 5);

		return {
			toolFrequency: Array.from(toolCounts.entries()).sort((a, b) => b[1] - a[1]),
			totalSessions,
			totalTasks,
			completedTasks,
			pendingTasks: totalTasks - completedTasks,
			dailyActivity,
			topProjects,
		};
	}

	private findLogDirectories(): TFolder[] {
		const dirs: TFolder[] = [];
		const logsName = this.settings.logsDirName;

		const walk = (folder: TFolder) => {
			for (const child of folder.children) {
				if (child instanceof TFolder) {
					if (child.name === logsName) {
						dirs.push(child);
					}
					// 只遍历一层深度（vault 直接子目录的项目）
					if (folder === this.app.vault.getRoot()) {
						walk(child);
					}
				}
			}
		};

		walk(this.app.vault.getRoot());
		return dirs;
	}

	private getLogFiles(dir: TFolder): TFile[] {
		const files: TFile[] = [];
		for (const child of dir.children) {
			if (child instanceof TFolder) {
				// 子目录（工具名目录）
				for (const f of child.children) {
					if (f instanceof TFile && f.extension === "md") {
						files.push(f);
					}
				}
			} else if (child instanceof TFile && child.extension === "md") {
				files.push(child);
			}
		}
		return files;
	}

	private async parseLogFile(file: TFile): Promise<LogEntry | null> {
		const cache = this.app.metadataCache.getFileCache(file);
		if (!cache?.frontmatter) return null;

		const fm = cache.frontmatter;
		const content = await this.app.vault.read(file);

		return {
			file,
			frontmatter: {
				tool: fm.tool || "",
				tool_version: fm.tool_version || "",
				session_id: fm.session_id || "",
				project: fm.project || "",
				project_path: fm.project_path || "",
				started: fm.started || "",
				ended: fm.ended || null,
				status: fm.status || "unknown",
				tags: fm.tags || [],
				handoff_to: fm.handoff_to || null,
			},
			summary: this.extractSection(content, "摘要"),
			tasks: this.extractTasks(content),
			decisions: this.extractListSection(content, "关键决策"),
			artifacts: this.extractListSection(content, "产出物"),
			context: {
				depends_on: fm["上下文传递"]?.depends_on || fm.depends_on || null,
				related_files: fm["上下文传递"]?.related_files || fm.related_files || null,
			},
		};
	}

	private extractSection(content: string, heading: string): string {
		const regex = new RegExp(`^## ${heading}\\s*\\n([\\s\\S]*?)(?=^## |$)`, "m");
		const match = content.match(regex);
		return match ? match[1].trim() : "";
	}

	private extractListSection(content: string, heading: string): string[] {
		const section = this.extractSection(content, heading);
		if (!section) return [];
		return section
			.split("\n")
			.filter((l) => l.trim().startsWith("- "))
			.map((l) => l.trim().replace(/^- /, "").replace(/`/g, "").trim());
	}

	private extractTasks(content: string): TaskItem[] {
		const section = this.extractSection(content, "任务清单");
		if (!section) return [];
		return section
			.split("\n")
			.filter((l) => l.trim().startsWith("- ["))
			.map((l) => {
				const completed = l.includes("[x]");
				const text = l.replace(/- \[[ x]\]\s*/, "").trim();
				return { text, completed };
			});
	}
}

export interface SearchFilters {
	tool?: string;
	project?: string;
	status?: string;
	dateFrom?: string;
	dateTo?: string;
	tags?: string[];
}

export interface StatsData {
	toolFrequency: [string, number][];
	totalSessions: number;
	totalTasks: number;
	completedTasks: number;
	pendingTasks: number;
	dailyActivity: Map<string, number>;
	topProjects: [string, number][];
}
