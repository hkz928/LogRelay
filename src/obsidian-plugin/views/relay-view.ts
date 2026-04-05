import { ItemView, WorkspaceLeaf, TFile } from "obsidian";
import LogRelayPlugin from "../main";
import { RelayNode } from "../services/log-parser";

export const RELAY_VIEW_TYPE = "logrelay-relay-view";

export class RelayView extends ItemView {
	plugin: LogRelayPlugin;
	private selectedProject: string = "";

	constructor(leaf: WorkspaceLeaf, plugin: LogRelayPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string {
		return RELAY_VIEW_TYPE;
	}

	getDisplayText(): string {
		return "LogRelay 接力链路";
	}

	getIcon(): string {
		return "git-branch";
	}

	async onOpen() {
		const container = this.containerEl.children[1] as HTMLElement;
		container.empty();
		container.classList.add("logrelay-relay-view");

		await this.plugin.logParser.refreshIndex();
		this.render(container);
	}

	private render(container: HTMLElement) {
		container.empty();

		// 标题
		const header = container.createDiv({ cls: "logrelay-header" });
		header.createEl("h3", { text: "接力链路" });

		// 项目选择器
		const projects = this.plugin.logParser.getAllProjects();
		if (projects.length === 0) {
			container.createEl("p", { text: "暂无日志数据。请先使用 LogRelay 记录工作会话。", cls: "logrelay-empty" });
			return;
		}

		const selector = container.createDiv({ cls: "logrelay-project-selector" });
		const select = selector.createEl("select");
		select.createEl("option", { text: "选择项目...", value: "" });
		for (const p of projects) {
			select.createEl("option", { text: p, value: p });
		}
		select.value = this.selectedProject;
		select.addEventListener("change", () => {
			this.selectedProject = select.value;
			this.renderRelayChain(container.createDiv({ cls: "logrelay-chain" }));
		});

		if (this.selectedProject) {
			this.renderRelayChain(container.createDiv({ cls: "logrelay-chain" }));
		}
	}

	private renderRelayChain(container: HTMLElement) {
		container.empty();

		if (!this.selectedProject) return;

		const nodes = this.plugin.logParser.buildRelayGraph(this.selectedProject);
		if (nodes.length === 0) {
			container.createEl("p", { text: "该项目暂无接力记录。", cls: "logrelay-empty" });
			return;
		}

		const projectLabel = container.createDiv({ cls: "logrelay-chain-project" });
		projectLabel.createEl("strong", { text: `项目：${this.selectedProject}` });

		const chain = container.createDiv({ cls: "logrelay-chain-nodes" });
		for (const node of nodes) {
			this.renderNode(chain, node, 0);
		}
	}

	private renderNode(container: HTMLElement, node: RelayNode, depth: number) {
		if (depth > this.plugin.settings.relayDisplayDepth) return;

		const nodeEl = container.createDiv({ cls: `logrelay-node logrelay-node-${node.status}` });

		// 点击跳转
		nodeEl.addEventListener("click", () => {
			this.app.workspace.getLeaf(false).openFile(node.file);
		});

		// 状态图标
		const icon = nodeEl.createSpan({ cls: "logrelay-node-icon" });
		icon.setText(this.getStatusIcon(node.status));

		// 信息
		const info = nodeEl.createDiv({ cls: "logrelay-node-info" });
		const date = node.started.slice(0, 10);
		info.createEl("span", { text: `[${date}] `, cls: "logrelay-node-date" });
		info.createEl("span", { text: node.tool, cls: "logrelay-node-tool" });

		const subject = nodeEl.createDiv({ cls: "logrelay-node-subject" });
		subject.setText(node.summary || "(无摘要)");

		// 子节点
		if (node.children.length > 0) {
			const connector = container.createDiv({ cls: "logrelay-connector" });
			connector.setText("▼");

			for (const child of node.children) {
				this.renderNode(container, child, depth + 1);
			}
		}
	}

	private getStatusIcon(status: string): string {
		switch (status) {
			case "completed": return "✅";
			case "active": return "🔵";
			case "paused": return "🟡";
			case "failed": return "🔴";
			default: return "⚪";
		}
	}

	async onClose() {}
}
