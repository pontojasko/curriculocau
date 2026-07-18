<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	let currentMode = $state<'single' | 'batch'>('single');

	// Single Mode State
	let jobDescription = $state('');
	let isRunning = $state(false);
	let isScraping = $state(false);
	let consoleOutput = $state('');
	let matchData = $state<any>(null);
	let pdfReady = $state(false);
	let pdfPath = $state('');
	let models = $state<any[]>([]);
	let selectedModel = $state('');

	let consoleElement: HTMLElement | undefined = $state();

	// Batch Mode State
	let batchKeywords = $state('');
	let batchLocation = $state('Brasil');
	let isSearching = $state(false);
	let batchJobs = $state<any[]>([]);
	let selectedBatchJobs = $state<Set<string>>(new Set());
	let isBatchRunning = $state(false);
	let batchStatusData = $state<any>(null);
	let batchInterval: any;
	let remoteOnly = $state(false);

	$effect(() => {
		// Auto-scroll the console output
		if (consoleOutput && consoleElement) {
			consoleElement.scrollTop = consoleElement.scrollHeight;
		}
	});

	// URL detection and scraping for Single Mode
	$effect(() => {
		const text = jobDescription.trim();
		const urlPattern = /^https?:\/\/[^\s]+$/;
		if (urlPattern.test(text) && !isScraping && !isRunning && currentMode === 'single') {
			extractJob(text);
		}
	});

	async function extractJob(url: string) {
		isScraping = true;
		consoleOutput += `\n[SYSTEM] Detectada URL da vaga. Iniciando extração...\n`;
		try {
			const res = await fetch('/api/scrape', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url })
			});
			const data = await res.json();
			
			if (!res.ok) {
				consoleOutput += `[ERROR] Falha na API (${res.status}): ${data.error || data.detail || 'Erro desconhecido'}\n`;
			} else if (data.error) {
				consoleOutput += `[ERROR] Falha ao extrair vaga: ${data.error}\n`;
			} else {
				const title = data.title ? data.title.trim() : 'Vaga';
				const desc = data.description ? data.description.trim() : '';
				jobDescription = `${title}\n\n${desc}`;
				consoleOutput += `[SUCCESS] Vaga extraída com sucesso! Iniciando análise...\n`;
				setTimeout(() => { runAnalysis(); }, 100);
			}
		} catch (e: any) {
			consoleOutput += `[ERROR] Erro na requisição de extração: ${e.message || e}\n`;
		} finally {
			isScraping = false;
		}
	}

	onMount(async () => {
		try {
			const response = await fetch('/api/models?t=' + new Date().getTime());
			const data = await response.json();
			if (data.models && Array.isArray(data.models)) {
				const modelRanking = [
					{ id: 'deepseek-ai/deepseek-v4-pro', score: 99 },
					{ id: 'meta/llama-3.3-70b-instruct', score: 96 },
					{ id: 'mistralai/mistral-large-3-675b-instruct-2512', score: 95 },
					{ id: 'meta/llama-3.1-70b-instruct', score: 93 },
					{ id: 'meta/llama-3.3-nemotron-super-49b-v1.5', score: 90 },
					{ id: 'deepseek-ai/deepseek-v4-flash', score: 88 },
					{ id: 'google/gemma-4-31b-it', score: 85 },
					{ id: 'nvidia/nvidia-nemotron-nano-9b-v2', score: 82 },
					{ id: 'meta/llama-3.1-8b-instruct', score: 78 },
					{ id: 'google/gemma-2-2b-it', score: 70 }
				];

				const filteredModels: any[] = [];
				modelRanking.forEach(rank => {
					const found = data.models.find((m: any) => m.id === rank.id);
					if (found) {
						filteredModels.push({
							...found,
							tag: ` (Score: ${rank.score})`
						});
					}
				});

				models = filteredModels;
				if (models.length > 0) {
					selectedModel = models[0].id;
				}
			}
		} catch (e) {
			console.error("Failed to load models", e);
			models = [{ id: 'meta/llama-3.1-8b-instruct', title: 'llama-3.1-8b-instruct', tag: ' (Default)' }];
			selectedModel = 'meta/llama-3.1-8b-instruct';
		}
	});

	async function runAnalysis() {
		if (!jobDescription.trim() || isRunning) return;

		isRunning = true;
		consoleOutput = '';
		matchData = null;
		pdfReady = false;
		pdfPath = '';

		try {
			consoleOutput += `[SYSTEM] Initializing analysis engine with model ${selectedModel}...\n`;
			
			const response = await fetch('/api/generate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ 
					job_description: jobDescription,
					model: selectedModel
				})
			});

			if (!response.ok) {
				consoleOutput += `[ERROR] Server returned ${response.status}: ${await response.text()}\n`;
				isRunning = false;
				return;
			}

			const reader = response.body?.getReader();
			const decoder = new TextDecoder('utf-8');

			if (!reader) throw new Error('No readable stream available.');

			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				
				buffer += decoder.decode(value, { stream: true });
				
				let newlineIndex;
				while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
					const line = buffer.slice(0, newlineIndex).trim();
					buffer = buffer.slice(newlineIndex + 1);
					
					if (line.startsWith('data: ')) {
						try {
							const jsonStr = line.substring(line.indexOf('{'));
							const data = JSON.parse(jsonStr);
							
							if (data.type === 'success') {
								consoleOutput += '\n[SUCCESS] Otimização concluída com sucesso!\n';
								pdfPath = data.message;
								pdfReady = true;
							} else if (data.type === 'analysis_stream_start') {
								consoleOutput += '\n[SYSTEM] Calculando Match Score e Gaps...\n';
							} else if (data.type === 'analysis_stream') {
								consoleOutput += data.message;
							} else if (data.type === 'analysis') {
								consoleOutput += '\n\n[SYSTEM] Diagnóstico estruturado carregado com sucesso.\n';
								try {
									matchData = JSON.parse(data.message);
								} catch (e) {}
							} else if (data.type === 'stream_start') {
								consoleOutput += '\n[SYSTEM] Recebendo resposta da IA...\n';
							} else if (data.type === 'stream') {
								consoleOutput += data.message;
							} else {
								consoleOutput += `\n[${data.type.toUpperCase()}] ${data.message}\n`;
							}
						} catch(e) {}
					}
				}
			}
		} catch (error: any) {
			consoleOutput += `\n[FATAL] ${error.message || error}\n`;
		} finally {
			isRunning = false;
		}
	}

	// Batch Mode Functions
	async function searchBatchJobs() {
		if (!batchKeywords.trim()) return;
		isSearching = true;
		try {
			const res = await fetch('/api/search-jobs', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ keywords: batchKeywords, location: batchLocation, remote_only: remoteOnly })
			});
			const data = await res.json();
			if (data.jobs) {
				batchJobs = data.jobs;
				selectedBatchJobs = new Set(data.jobs.map((j: any) => j.id));
			}
		} catch (e) {
			console.error(e);
		} finally {
			isSearching = false;
		}
	}

	function toggleJobSelection(id: string) {
		const newSet = new Set(selectedBatchJobs);
		if (newSet.has(id)) newSet.delete(id);
		else newSet.add(id);
		selectedBatchJobs = newSet;
	}

	async function startBatchProcess() {
		const jobsToProcess = batchJobs.filter(j => selectedBatchJobs.has(j.id));
		if (jobsToProcess.length === 0) return;
		
		isBatchRunning = true;
		batchStatusData = null;
		
		try {
			await fetch('/api/batch-process', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ jobs: jobsToProcess, model: selectedModel })
			});
			
			startPollingBatchStatus();
		} catch (e) {
			console.error(e);
			isBatchRunning = false;
		}
	}

	function startPollingBatchStatus() {
		if (batchInterval) clearInterval(batchInterval);
		batchInterval = setInterval(async () => {
			try {
				const res = await fetch('/api/batch-status');
				const data = await res.json();
				batchStatusData = data;
				
				if (data.status === 'completed' || data.status === 'idle') {
					clearInterval(batchInterval);
					isBatchRunning = false;
				}
			} catch (e) {
				console.error(e);
			}
		}, 2000);
	}

	onDestroy(() => {
		if (batchInterval) clearInterval(batchInterval);
	});
</script>

<svelte:head>
	<title>curriculo-cau</title>
</svelte:head>

<div class="flex h-screen w-full bg-gb-bg text-gb-fg">
	<!-- Left Pane: Input -->
	<div class="flex flex-col w-1/2 border-r border-gb-bg-soft p-8">
		<header class="mb-6">
			<div class="flex justify-between items-start">
				<div>
					<h1 class="text-2xl font-display font-bold text-gb-yellow uppercase tracking-wider">curriculo-cau</h1>
					<p class="text-gb-gray mt-2 font-mono text-sm">Curriculum Analyzer & Upgrader. Local LaTeX synthesis engine.</p>
				</div>
				
				<!-- Mode Toggle (Aesthetic Risk: Physical terminal switch style) -->
				<div class="flex bg-gb-bg-soft border border-gb-bg-soft p-1 shrink-0 ml-4">
					<button 
						onclick={() => currentMode = 'single'}
						class="px-4 py-2 font-mono text-xs uppercase tracking-wider transition-colors {currentMode === 'single' ? 'bg-gb-yellow text-gb-bg font-bold' : 'text-gb-gray hover:text-gb-fg'}"
					>
						[ Single ]
					</button>
					<button 
						onclick={() => currentMode = 'batch'}
						class="px-4 py-2 font-mono text-xs uppercase tracking-wider transition-colors {currentMode === 'batch' ? 'bg-gb-yellow text-gb-bg font-bold' : 'text-gb-gray hover:text-gb-fg'}"
					>
						[ Batch ]
					</button>
				</div>
			</div>
		</header>

		<!-- Model Selector (Shared) -->
		<div class="mb-6">
			<label for="model-select" class="block text-gb-gray font-mono text-xs uppercase tracking-wider mb-2">Select AI Model</label>
			<select 
				id="model-select"
				bind:value={selectedModel}
				disabled={isRunning || isBatchRunning}
				class="w-full bg-gb-bg-soft border border-gb-bg-soft rounded-none p-3 font-mono text-sm text-gb-fg focus:outline-none focus:border-gb-yellow transition-colors cursor-pointer"
			>
				{#each models as model}
					<option value={model.id}>{model.title}{model.tag}</option>
				{/each}
			</select>
		</div>

		{#if currentMode === 'single'}
			<!-- SINGLE MODE INPUT -->
			<div class="flex-1 flex flex-col min-h-0 relative">
				<label for="job-desc" class="block text-gb-gray font-mono text-xs uppercase tracking-wider mb-2">Job Description / Link</label>
				<textarea 
					id="job-desc"
					bind:value={jobDescription}
					class="flex-1 w-full bg-gb-bg-soft border border-gb-bg-soft p-4 font-mono text-sm focus:outline-none focus:border-gb-yellow resize-none transition-colors"
					placeholder="Paste job description OR job link here..."
					disabled={isRunning || isScraping}
				></textarea>
				{#if isScraping}
					<div class="absolute inset-0 flex flex-col items-center justify-center bg-gb-bg-soft/80 backdrop-blur-sm z-10">
						<span class="w-8 h-8 rounded-full border-2 border-gb-yellow border-t-transparent animate-spin mb-4"></span>
						<p class="text-gb-yellow font-mono text-sm font-bold uppercase tracking-widest animate-pulse">Extracting Job Data...</p>
					</div>
				{/if}
			</div>

			<div class="mt-6">
				<button 
					onclick={runAnalysis}
					disabled={isRunning || !jobDescription.trim()}
					class="w-full py-4 font-display font-bold text-gb-bg bg-gb-yellow hover:bg-gb-orange disabled:opacity-50 disabled:cursor-not-allowed transition-colors uppercase tracking-widest cursor-pointer"
				>
					{isRunning ? 'Compiling...' : 'Run Analysis'}
				</button>
			</div>
		{:else}
			<!-- BATCH MODE INPUT -->
			<div class="mb-4 flex gap-4">
				<div class="flex-1">
					<label for="batch-keywords" class="block text-gb-gray font-mono text-xs uppercase tracking-wider mb-2">Palavras-chave</label>
					<input 
						id="batch-keywords"
						bind:value={batchKeywords}
						class="w-full bg-gb-bg-soft border border-gb-bg-soft p-3 font-mono text-sm focus:outline-none focus:border-gb-yellow transition-colors text-gb-fg"
						placeholder="ex: Desenvolvedor Java React"
						disabled={isSearching || isBatchRunning}
					/>
				</div>
				<div class="w-1/3">
					<label for="batch-location" class="block text-gb-gray font-mono text-xs uppercase tracking-wider mb-2">Localização</label>
					<input 
						id="batch-location"
						bind:value={batchLocation}
						class="w-full bg-gb-bg-soft border border-gb-bg-soft p-3 font-mono text-sm focus:outline-none focus:border-gb-yellow transition-colors text-gb-fg"
						disabled={isSearching || isBatchRunning}
					/>
				</div>
			</div>

			<!-- Retro physical toggle for remote-only (Aesthetic risk aligning with frontend-design) -->
			<div class="mb-4 flex items-center justify-between bg-gb-bg-soft p-3 border border-gb-bg-soft shrink-0">
				<span class="text-gb-gray font-mono text-xs uppercase tracking-wider">Apenas Vagas Remotas</span>
				<button 
					onclick={() => remoteOnly = !remoteOnly}
					disabled={isSearching || isBatchRunning}
					class="px-3 py-1.5 font-mono text-xs uppercase border transition-all cursor-pointer {remoteOnly ? 'border-gb-green text-gb-green bg-gb-green/10' : 'border-gb-gray text-gb-gray hover:text-gb-fg'}"
				>
					{remoteOnly ? '[ Remoto: Ativo ]' : '[ Remoto: Inativo ]'}
				</button>
			</div>
			
			<button 
				onclick={searchBatchJobs}
				disabled={isSearching || isBatchRunning || !batchKeywords.trim()}
				class="w-full py-3 mb-6 font-display font-bold text-gb-bg bg-gb-yellow hover:bg-gb-orange disabled:opacity-50 disabled:cursor-not-allowed transition-colors uppercase tracking-widest cursor-pointer"
			>
				{isSearching ? 'Buscando...' : 'Buscar Vagas'}
			</button>

			{#if batchJobs.length > 0}
				<div class="flex-1 flex flex-col min-h-0 border border-gb-bg-soft bg-gb-bg">
					<div class="p-3 bg-gb-bg-soft flex justify-between items-center shrink-0 border-b border-gb-bg">
						<span class="font-mono text-xs uppercase tracking-wider text-gb-gray">Vagas Encontradas ({batchJobs.length})</span>
						<span class="font-mono text-xs text-gb-yellow">{selectedBatchJobs.size} selecionadas</span>
					</div>
					<div class="flex-1 overflow-auto p-2">
						{#each batchJobs as job}
							<button 
								onclick={() => toggleJobSelection(job.id)}
								disabled={isBatchRunning}
								class="w-full flex items-start text-left p-3 mb-2 border hover:border-gb-yellow transition-colors {selectedBatchJobs.has(job.id) ? 'border-gb-yellow bg-gb-bg-soft' : 'border-gb-bg-soft bg-gb-bg'}"
							>
								<div class="mr-4 mt-1 text-gb-yellow font-bold font-mono">
									{selectedBatchJobs.has(job.id) ? '[X]' : '[ ]'}
								</div>
								<div class="flex-1 overflow-hidden">
									<div class="font-bold text-gb-fg truncate">{job.title}</div>
									<div class="text-xs text-gb-gray font-mono mt-1 flex justify-between">
										<span class="truncate pr-2">{job.company}</span>
										<span class="shrink-0">{job.location}</span>
									</div>
								</div>
							</button>
						{/each}
					</div>
				</div>

				<div class="mt-6 shrink-0">
					<button 
						onclick={startBatchProcess}
						disabled={isBatchRunning || selectedBatchJobs.size === 0}
						class="w-full py-4 font-display font-bold text-gb-bg bg-gb-green hover:bg-[#98971a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors uppercase tracking-widest cursor-pointer"
					>
						{isBatchRunning ? 'Processando Lote...' : 'Otimizar Vagas Selecionadas'}
					</button>
				</div>
			{/if}
		{/if}
	</div>

	<!-- Right Pane: Output -->
	<div class="flex flex-col w-1/2 p-8 overflow-hidden bg-gb-bg/50 relative">
		{#if currentMode === 'single'}
			<!-- SINGLE MODE OUTPUT -->
			<header class="mb-8 flex justify-between items-end shrink-0">
				<h2 class="text-lg font-display font-bold text-gb-fg uppercase tracking-wider">Diagnostic Console</h2>
				<div class="flex items-center gap-2">
					<span class="w-2 h-2 rounded-full {isRunning ? 'bg-gb-orange animate-pulse' : 'bg-gb-green'}"></span>
					<span class="text-gb-gray font-mono text-xs">{isRunning ? 'EXECUTING' : 'IDLE'}</span>
				</div>
			</header>

			{#if matchData}
				<div class="mb-6 p-6 border border-gb-bg-soft bg-gb-bg flex flex-col gap-4 shrink-0">
					<div class="flex items-center justify-between">
						<h3 class="font-display text-gb-yellow font-bold uppercase tracking-wider">Match Report</h3>
						<div class="text-3xl font-mono font-bold {matchData.matchScore >= 80 ? 'text-gb-green' : matchData.matchScore >= 50 ? 'text-gb-yellow' : 'text-gb-red'}">
							{matchData.matchScore}%
						</div>
					</div>
					
					{#if matchData.gaps && matchData.gaps.length > 0}
						<div class="mt-4">
							<h4 class="text-gb-gray text-xs uppercase tracking-wider mb-3">Identified Gaps</h4>
							<div class="flex flex-wrap gap-2">
								{#each matchData.gaps as gap}
									<span class="px-2 py-1 text-xs font-mono border border-gb-orange text-gb-orange bg-gb-orange/10">
										{gap.keyword}
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}

			<div 
				bind:this={consoleElement}
				class="flex-1 overflow-auto bg-gb-bg border border-gb-bg-soft p-4 font-mono text-xs text-gb-gray whitespace-pre-wrap leading-relaxed shadow-inner"
			>
				{#if !consoleOutput}
					<span class="opacity-50">Waiting for input...</span>
				{:else}
					{consoleOutput}
				{/if}
			</div>

			{#if pdfReady}
				<div class="mt-6 shrink-0">
					<a 
						href={`/api/download?path=${encodeURIComponent(pdfPath)}`}
						download="resume.pdf"
						class="block text-center w-full py-4 font-display font-bold text-gb-bg bg-gb-green hover:bg-[#98971a] transition-colors uppercase tracking-widest cursor-pointer"
					>
						Download Generated PDF
					</a>
				</div>
			{/if}

		{:else}
			<!-- BATCH MODE OUTPUT -->
			<header class="mb-8 flex justify-between items-end shrink-0">
				<h2 class="text-lg font-display font-bold text-gb-fg uppercase tracking-wider">Status do Lote</h2>
				<div class="flex items-center gap-2">
					<span class="w-2 h-2 rounded-full {isBatchRunning ? 'bg-gb-orange animate-pulse' : 'bg-gb-green'}"></span>
					<span class="text-gb-gray font-mono text-xs">{isBatchRunning ? 'PROCESSANDO' : 'OCIOSO'}</span>
				</div>
			</header>

			<div class="flex-1 overflow-auto min-h-[40%]">
				{#if !batchStatusData || !batchStatusData.jobs || Object.keys(batchStatusData.jobs).length === 0}
					<div class="h-full flex items-center justify-center border border-gb-bg-soft border-dashed text-gb-gray font-mono text-sm">
						Nenhum lote em andamento.
					</div>
				{:else}
					<div class="flex flex-col gap-4 pr-2">
						{#each Object.entries(batchStatusData.jobs) as [id, statusJob]: [string, any]}
							<div class="border border-gb-bg-soft bg-gb-bg p-4 flex flex-col gap-3">
								<div class="flex justify-between items-start">
									<div class="font-bold text-gb-fg flex-1 mr-4 break-words">{statusJob.title}</div>
									
									<div class="px-2 py-1 text-[10px] font-mono uppercase tracking-wider border shrink-0
										{statusJob.status === 'completed' ? 'border-gb-green text-gb-green bg-gb-green/10' :
										 statusJob.status === 'failed' ? 'border-gb-red text-gb-red bg-gb-red/10' :
										 statusJob.status === 'scraping' ? 'border-gb-orange text-gb-orange bg-gb-orange/10 animate-pulse' :
										 statusJob.status === 'generating' ? 'border-gb-yellow text-gb-yellow bg-gb-yellow/10 animate-pulse' :
										 'border-gb-gray text-gb-gray'}"
									>
										{statusJob.status}
									</div>
								</div>
								
								<div class="text-xs text-gb-gray font-mono flex items-center gap-2">
									<span>{statusJob.company}</span>
									<span>&bull;</span>
									<a href={statusJob.url} target="_blank" rel="noopener noreferrer" class="text-gb-blue hover:underline">Ver vaga</a>
								</div>
								
								{#if statusJob.error}
									<div class="text-xs text-gb-red font-mono bg-gb-red/10 p-2 border border-gb-red/20 break-words whitespace-pre-wrap">
										[ERROR] {statusJob.error}
									</div>
								{/if}

								{#if statusJob.status === 'completed' && statusJob.pdf_path}
									<div class="mt-2 flex justify-end">
										<a 
											href={`/api/download?path=${encodeURIComponent(statusJob.pdf_path)}`}
											download
											class="px-4 py-2 text-xs font-mono font-bold text-gb-bg bg-gb-green hover:bg-[#98971a] transition-colors"
										>
											[ Download PDF ]
										</a>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- BATCH CONSOLE OUTPUT -->
			<div 
				bind:this={consoleElement}
				class="mt-6 flex-1 min-h-[30%] overflow-auto bg-gb-bg border border-gb-bg-soft p-4 font-mono text-xs text-gb-gray whitespace-pre-wrap leading-relaxed shadow-inner"
			>
				{#if !batchStatusData || !batchStatusData.logs}
					<span class="opacity-50">Waiting for batch logs...</span>
				{:else}
					{batchStatusData.logs}
				{/if}
			</div>
		{/if}
	</div>
</div>
