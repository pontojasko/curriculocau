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
	let scrapedJobUrl = $state<string | null>(null);
	let scrapedApplyType = $state<string | null>(null);
	let awaitingConfirmation = $state(false);
	let confirmationSessionId = $state('');

	let consoleElement: HTMLElement | undefined = $state();

	// Batch Mode State
	let isSearching = $state(false);
	let keywordTags = $state<string[]>([]);
	let currentKeyword = $state('');
	let negativeTags = $state<string[]>([]);
	let currentNegative = $state('');
	// batchNegativeKeywords replaced by negativeTags
	let batchLocation = $state('Brasil');
	let remoteOnly = $state(true);
	let batchJobs = $state<any[]>([]);
	let selectedBatchJobs = $state<Set<string>>(new Set());
	let isBatchRunning = $state(false);
	let batchStatusData = $state<any>(null);
	let batchInterval: any;
	let singleConsoleElement: HTMLElement | undefined = $state();
	let batchConsoleElement: HTMLElement | undefined = $state();

	// Pools of suggestions
	const keywordPool = [
		'Desenvolvedor', 'React', 'Python', 'Node', 'Java', 'TypeScript', 'Svelte', 
		'Vue', 'Angular', 'Go', 'Rust', 'Ruby', 'PHP', 'C#', 'C++', 'Docker', 
		'Kubernetes', 'AWS', 'Azure', 'SQL', 'NoSQL', 'DevOps', 'Frontend', 'Backend', 
		'Fullstack', 'Mobile', 'Flutter', 'React Native', 'Data Science', 'Machine Learning',
		'Elixir', 'Django', 'Flask', 'Spring Boot', 'Laravel', 'Next.js', 'NestJS', 'GraphQL',
		'APIs', 'Microserviços', 'CSS', 'Tailwind', 'PostgreSQL', 'MongoDB', 'Redis', 'Linux'
	];
	const negativePool = [
		'Senior', 'Pleno', 'Estágio', 'Junior', 'Presencial', 'Híbrido', 'CLT', 'PJ', 
		'Temporário', 'Voluntário', 'Gerente', 'Diretor', 'Coordenador', 'QA', 'Tester', 
		'Design', 'UX', 'Product Owner', 'Scrum Master', 'Sales', 'Vendas', 'Suporte', 
		'Atendimento', 'Marketing', 'Finanças', 'Jurídico', 'RH', 'Recruiter', 'Consultor'
	];

	let displayedKeywords = $state<string[]>(['Desenvolvedor', 'React', 'Python', 'Node']);
	let displayedNegatives = $state<string[]>(['Senior', 'Pleno', 'Estágio', 'Presencial']);

	function rotateKeywords() {
		const shuffled = [...keywordPool].sort(() => 0.5 - Math.random());
		displayedKeywords = shuffled.slice(0, 4);
	}

	function rotateNegatives() {
		const shuffled = [...negativePool].sort(() => 0.5 - Math.random());
		displayedNegatives = shuffled.slice(0, 4);
	}


	$effect(() => {
		// Auto-scroll the single console output
		if (consoleOutput && singleConsoleElement) {
			singleConsoleElement.scrollTop = singleConsoleElement.scrollHeight;
		}
	});

	$effect(() => {
		// Auto-scroll the batch console output
		if (batchStatusData?.logs && batchConsoleElement) {
			batchConsoleElement.scrollTop = batchConsoleElement.scrollHeight;
		}
	});

	// Persist changes to localStorage
	$effect(() => {
		localStorage.setItem('cau_batch_keywords', JSON.stringify(keywordTags));
		localStorage.setItem('cau_batch_negative_keywords', JSON.stringify(negativeTags));
	});

	$effect(() => {
		localStorage.setItem('cau_remote_only', String(remoteOnly));
	});

	$effect(() => {
		if (selectedModel) {
			localStorage.setItem('cau_selected_model', selectedModel);
		}
	});

	// URL detection and scraping for Single Mode
	$effect(() => {
		const text = jobDescription.trim();
		const urlPattern = /^https?:\/\/[^\s]+$/;
		if (urlPattern.test(text) && !isScraping && !isRunning && currentMode === 'single') {
			extractJob(text);
		} else if (scrapedJobUrl && !text.includes(scrapedJobUrl) && !isScraping) {
			// If user clears the text or replaces it manually, reset the scraped url
			scrapedJobUrl = null;
			scrapedApplyType = null;
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
				scrapedJobUrl = url;
				scrapedApplyType = data.apply_type || null;
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
		// Recover states from localStorage
		const storedKeys = localStorage.getItem('cau_batch_keywords');
		if (storedKeys) {
			try { keywordTags = JSON.parse(storedKeys); }
			catch { keywordTags = storedKeys.split(' ').filter(Boolean); }
		}
		
		const storedNegKeys = localStorage.getItem('cau_batch_negative_keywords');
		if (storedNegKeys) {
			try { negativeTags = JSON.parse(storedNegKeys); }
			catch { negativeTags = storedNegKeys.split(' ').filter(Boolean); }
		}

		const cachedRemote = localStorage.getItem('cau_remote_only');
		if (cachedRemote) remoteOnly = cachedRemote === 'true';

		try {
			const response = await fetch('/api/models?t=' + new Date().getTime());
			const data = await response.json();
			if (data.models && Array.isArray(data.models)) {
				const modelRanking = [
					{ id: 'deepseek-ai/deepseek-v4-pro', score: 99 },
					{ id: 'gemini-1.5-pro', score: 97 },
					{ id: 'meta/llama-3.3-70b-instruct', score: 96 },
					{ id: 'mistralai/mistral-large-3-675b-instruct-2512', score: 95 },
					{ id: 'meta/llama-3.1-70b-instruct', score: 93 },
					{ id: 'gemini-2.0-flash', score: 92 },
					{ id: 'meta/llama-3.3-nemotron-super-49b-v1.5', score: 90 },
					{ id: 'gemini-1.5-flash', score: 89 },
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
				
				const cachedModel = localStorage.getItem('cau_selected_model');
				if (cachedModel && models.some(m => m.id === cachedModel)) {
					selectedModel = cachedModel;
				} else if (models.length > 0) {
					selectedModel = models[0].id;
				}
			}
		} catch (e) {
			console.error("Failed to load models", e);
			const cachedModel = localStorage.getItem('cau_selected_model');
			models = [{ id: 'meta/llama-3.1-8b-instruct', title: 'llama-3.1-8b-instruct', tag: ' (Default)' }];
			selectedModel = cachedModel || 'meta/llama-3.1-8b-instruct';
		}
	});

	async function runAnalysis() {
		if (!jobDescription.trim() || isRunning) return;

		isRunning = true;
		consoleOutput = '';
		matchData = null;
		pdfReady = false;
		pdfPath = '';
		awaitingConfirmation = false;
		confirmationSessionId = '';

		try {
			consoleOutput += `[SYSTEM] Initializing analysis engine with model ${selectedModel}...\n`;
			
			const response = await fetch('/api/generate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ 
					job_description: jobDescription,
					model: selectedModel,
					job_url: scrapedJobUrl,
					apply_type: scrapedApplyType
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
								const msg = data.message;
								if (msg.includes("[ACTION_REQUIRED:")) {
									const match = msg.match(/\[ACTION_REQUIRED:([^\]]+)\]/);
									if (match) {
										confirmationSessionId = match[1];
										awaitingConfirmation = true;
									}
								}
								consoleOutput += `\n[${data.type.toUpperCase()}] ${msg}\n`;
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

	async function confirmApply() {
		if (!confirmationSessionId) return;
		awaitingConfirmation = false;
		consoleOutput += '\n[SYSTEM] Enviando confirmação...\n';
		try {
			await fetch(`/api/confirm-apply/${confirmationSessionId}`, { method: 'POST' });
		} catch(e) {}
	}

	// Batch Mode Functions
	async function searchBatchJobs() {
		if (keywordTags.length === 0) return;
		isSearching = true;
		batchJobs = [];
		selectedBatchJobs.clear();
		
		try {
			const res = await fetch('/api/search-jobs', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					keywords: keywordTags.join(' '),
					negative_keywords: negativeTags.join(', '),
					location: batchLocation,
					remote_only: remoteOnly
				})
			});
			if (!res.body) throw new Error("No response body");
			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				
				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || ''; // Mantém a linha incompleta (se houver) no buffer
				
				for (const line of lines) {
					if (line.trim()) {
						try {
							const obj = JSON.parse(line);
							if (obj.error) {
								consoleOutput += `\n[ERROR] ${obj.error}\n`;
							} else {
								batchJobs = [...batchJobs, obj];
								const newSet = new Set(selectedBatchJobs);
								newSet.add(obj.id);
								selectedBatchJobs = newSet;
							}
						} catch (e) {
							console.error("Falha ao analisar JSON do stream", e);
						}
					}
				}
			}
		} catch (error: any) {
			consoleOutput += `\n[FATAL] ${error.message || error}\n`;
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

	async function clearCache() {
		try {
			await fetch('/api/clear-cache', { method: 'DELETE' });
			batchJobs = [];
			selectedBatchJobs = new Set();
			if (!batchStatusData) batchStatusData = {};
			batchStatusData.logs = (batchStatusData.logs || '') + "\n[SYSTEM] Cache de vagas limpo. Histórico deletado.\n";
		} catch (e) {
			console.error(e);
		}
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
					<h1 class="text-2xl font-sans font-bold text-gb-yellow uppercase tracking-wider">curriculo-cau</h1>
					<p class="text-gb-gray mt-2 font-mono text-sm">Curriculum Analyzer & Upgrader. Local LaTeX synthesis engine.</p>
				</div>
				
				<!-- Mode Toggle (Aesthetic Risk: Physical terminal switch style) -->
				<div class="flex bg-gb-bg-soft border border-gb-bg-soft p-1 shrink-0 ml-4">
					<button 
						onclick={() => currentMode = 'single'}
						class="px-4 py-2 font-mono text-xs uppercase tracking-wider  {currentMode === 'single' ? 'bg-gb-yellow text-gb-bg font-bold' : 'text-gb-gray hover:text-gb-fg'}"
					>
						[ Single ]
					</button>
					<button 
						onclick={() => currentMode = 'batch'}
						class="px-4 py-2 font-mono text-xs uppercase tracking-wider  {currentMode === 'batch' ? 'bg-gb-yellow text-gb-bg font-bold' : 'text-gb-gray hover:text-gb-fg'}"
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
				class="w-full bg-gb-bg-soft border border-gb-bg-soft rounded-none p-3 font-mono text-sm text-gb-fg focus:outline-none focus:border-gb-yellow  cursor-pointer"
			>
				{#each models as model}
					<option value={model.id}>{model.title}{model.tag}</option>
				{/each}
			</select>
		</div>

		{#if currentMode === 'single'}
			<!-- SINGLE MODE INPUT -->
			<div class="flex-1 flex flex-col min-h-0 border border-gb-bg-soft bg-gb-bg relative mb-4">
				<div class="p-3 bg-gb-bg-soft border-b border-gb-bg flex justify-between items-center shrink-0">
					<span class="font-mono text-xs uppercase tracking-wider text-gb-gray">Job Analysis Configuration</span>
				</div>
				<textarea 
					id="job-desc"
					bind:value={jobDescription}
					class="flex-1 w-full bg-gb-bg border-0 p-4 font-mono text-sm focus:outline-none resize-none text-gb-fg"
					placeholder="Paste job description OR job link here..."
					disabled={isRunning || isScraping}
				></textarea>
				{#if isScraping}
					<div class="absolute inset-0 top-[40px] flex flex-col items-center justify-center bg-gb-bg-soft/90 z-10">
						<div class="px-6 py-3 border border-gb-yellow bg-gb-bg text-gb-yellow font-mono text-xs font-bold uppercase tracking-widest">
							[ EXTRACTING JOB DATA... ]
						</div>
					</div>
				{/if}
				<div class="sticky bottom-0 bg-gb-bg-soft border-t border-gb-bg p-3 shrink-0 flex justify-end">
					<button 
						onclick={runAnalysis}
						disabled={isRunning || !jobDescription.trim()}
						class="px-6 py-2 font-sans font-bold text-gb-bg bg-gb-yellow hover:bg-gb-orange disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs cursor-pointer"
					>
						{isRunning ? 'Processing...' : 'Run Analysis'}
					</button>
				</div>
			</div>

		{:else}
			<!-- BATCH MODE INPUT -->
			<div class="flex flex-col gap-0 border border-gb-bg-soft bg-gb-bg mb-4 flex-1 min-h-0">
				<div class="p-3 bg-gb-bg-soft border-b border-gb-bg flex justify-between items-center shrink-0">
					<span class="font-mono text-xs uppercase tracking-wider text-gb-gray">Search Criteria</span>
				</div>
				<div class="p-6 flex flex-col gap-8 flex-1 overflow-auto">
					
					<div class="flex gap-4">
						<div class="flex-1">
							<label class="block text-gb-gray font-mono text-[10px] uppercase mb-2">Palavras-chave</label>
							
							<div class="w-full bg-gb-bg border border-gb-bg-soft p-2 flex flex-wrap gap-2 focus-within:border-gb-yellow/50 items-center min-h-[42px]">
								{#each keywordTags as tag, index}
									<div class="bg-gb-yellow/10 border border-gb-yellow/30 text-gb-yellow/80 text-[10px] font-mono px-2 py-1 flex items-center gap-2 uppercase">
										<span>{tag}</span>
										<button onclick={() => keywordTags.splice(index, 1)} class="text-gb-yellow/50 hover:text-gb-yellow font-bold">×</button>
									</div>
								{/each}
								<input 
									bind:value={currentKeyword}
									onkeydown={(e) => {
										if (e.key === 'Enter' && currentKeyword.trim()) {
											e.preventDefault();
											if (!keywordTags.includes(currentKeyword.trim())) keywordTags.push(currentKeyword.trim());
											currentKeyword = '';
										}
									}}
									class="flex-1 min-w-[120px] bg-transparent outline-none font-mono text-xs text-gb-fg/90" 
									placeholder={keywordTags.length === 0 ? "Type and press Enter" : ""}
									disabled={isSearching || isBatchRunning} 
								/>
							</div>
							
							<div class="flex flex-wrap gap-2 mt-3 items-center">
								{#each displayedKeywords as keyword}
									<button onclick={() => !keywordTags.includes(keyword) && keywordTags.push(keyword)} class="px-3 py-1 bg-gb-bg-soft border border-gb-bg-soft text-[9px] text-gb-gray hover:border-gb-yellow/30 hover:text-gb-yellow/80 uppercase tracking-widest cursor-pointer">
										{keyword}
									</button>
								{/each}
								<button onclick={rotateKeywords} class="px-2 py-1 bg-gb-bg border border-gb-bg-soft text-[9px] text-gb-yellow hover:bg-gb-yellow/10 uppercase font-bold cursor-pointer" title="Recarregar sugestões">
									⟳
								</button>
							</div>
						</div>
						
						<div class="w-1/3">
							<label class="block text-gb-gray font-mono text-[10px] uppercase mb-2">Local</label>
							<select bind:value={batchLocation} class="w-full bg-gb-bg border border-gb-bg-soft p-2 font-mono text-xs text-gb-fg/90 focus:outline-none focus:border-gb-yellow/50 uppercase h-[42px]" disabled={isSearching || isBatchRunning}>
								<option value="Brasil">Brasil</option>
								<option value="São Paulo">São Paulo</option>
								<option value="Rio de Janeiro">Rio de Janeiro</option>
								<option value="United States">Estados Unidos</option>
								<option value="Canada">Canadá</option>
								<option value="Portugal">Portugal</option>
								<option value="Europe">Europa</option>
							</select>
						</div>
					</div>
					
					<div>
						<label class="block text-gb-gray font-mono text-[10px] uppercase mb-2">Palavras Banidas (Negras)</label>
						
						<div class="w-full bg-gb-bg border border-gb-bg-soft p-2 flex flex-wrap gap-2 focus-within:border-gb-red/50 items-center min-h-[42px]">
							{#each negativeTags as tag, index}
								<div class="bg-gb-red/10 border border-gb-red/30 text-gb-red/70 text-[10px] font-mono px-2 py-1 flex items-center gap-2 uppercase">
									<span>{tag}</span>
									<button onclick={() => negativeTags.splice(index, 1)} class="text-gb-red/50 hover:text-gb-red font-bold">×</button>
								</div>
							{/each}
							<input 
								bind:value={currentNegative}
								onkeydown={(e) => {
									if (e.key === 'Enter' && currentNegative.trim()) {
										e.preventDefault();
										if (!negativeTags.includes(currentNegative.trim())) negativeTags.push(currentNegative.trim());
										currentNegative = '';
									}
								}}
								class="flex-1 min-w-[120px] bg-transparent outline-none font-mono text-xs text-gb-fg/90" 
								placeholder={negativeTags.length === 0 ? "Type and press Enter" : ""}
								disabled={isSearching || isBatchRunning} 
							/>
						</div>
						
						<div class="flex flex-wrap gap-2 mt-3 items-center">
							{#each displayedNegatives as negative}
								<button onclick={() => !negativeTags.includes(negative) && negativeTags.push(negative)} class="px-3 py-1 bg-gb-bg-soft border border-gb-bg-soft text-[9px] text-gb-gray hover:border-gb-red/30 hover:text-gb-red/70 uppercase tracking-widest cursor-pointer">
									{negative}
								</button>
							{/each}
							<button onclick={rotateNegatives} class="px-2 py-1 bg-gb-bg border border-gb-bg-soft text-[9px] text-gb-red hover:bg-gb-red/10 uppercase font-bold cursor-pointer" title="Recarregar sugestões">
								⟳
							</button>
						</div>
					</div>
					
				</div>
				
				<div class="flex items-center justify-between p-4 border-t border-gb-bg-soft bg-gb-bg shrink-0">
					<button onclick={() => remoteOnly = !remoteOnly} disabled={isSearching || isBatchRunning} class="font-mono text-[10px] uppercase {remoteOnly ? 'text-gb-green/80' : 'text-gb-gray'} cursor-pointer hover:text-gb-fg">
						[ {remoteOnly ? 'X' : ' '} ] Apenas Remoto
					</button>
					<button onclick={searchBatchJobs} disabled={isSearching || isBatchRunning || keywordTags.length === 0} class="px-8 py-3 font-sans font-bold text-gb-bg bg-gb-yellow/80 hover:bg-gb-yellow disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs cursor-pointer">
						{isSearching ? 'Buscando...' : 'Buscar Vagas'}
					</button>
				</div>
			</div>

			{#if batchJobs.length > 0}
				<div class="flex-1 flex flex-col min-h-0 border border-gb-bg-soft bg-gb-bg relative">
					<div class="p-3 bg-gb-bg-soft flex justify-between items-center shrink-0 border-b border-gb-bg">
						<span class="font-mono text-xs uppercase tracking-wider text-gb-gray">Queue ({batchJobs.length})</span>
						<span class="font-mono text-xs text-gb-yellow">{selectedBatchJobs.size} selected</span>
					</div>
					<div class="flex-1 overflow-auto">
						<table class="w-full text-left font-mono text-xs">
							<thead class="sticky top-0 bg-gb-bg-soft text-gb-gray uppercase text-[10px] z-10 border-b border-gb-bg">
								<tr>
									<th class="p-2 w-12 text-center">Sel</th>
									<th class="p-2">Role</th>
									<th class="p-2 w-32 truncate">Company</th>
								</tr>
							</thead>
							<tbody>
								{#each batchJobs as job}
									<tr class="border-b border-gb-bg-soft hover:bg-gb-bg-soft cursor-pointer {selectedBatchJobs.has(job.id) ? 'bg-gb-bg-soft' : ''}" onclick={() => toggleJobSelection(job.id)}>
										<td class="p-2 text-center text-gb-yellow font-bold whitespace-nowrap">
											{selectedBatchJobs.has(job.id) ? '[X]' : '[ ]'}
										</td>
										<td class="p-2 text-gb-fg truncate max-w-[200px]" title={job.title}>{job.title}</td>
										<td class="p-2 text-gb-gray truncate max-w-[120px]" title={job.company}>{job.company}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
					<div class="sticky bottom-0 bg-gb-bg-soft border-t border-gb-bg p-3 shrink-0 flex justify-between items-center shadow-[0_-10px_20px_rgba(40,40,40,0.8)]">
						<span class="font-mono text-xs text-gb-gray">{selectedBatchJobs.size} ready for processing</span>
						<button onclick={startBatchProcess} disabled={isBatchRunning || selectedBatchJobs.size === 0} class="px-6 py-2 font-sans font-bold text-gb-bg bg-gb-green hover:bg-[#98971a] disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs cursor-pointer">
							{isBatchRunning ? 'Processando...' : 'Iniciar Lote'}
						</button>
					</div>
				</div>
			{/if}
		{/if}

		<!-- Footer options: Purge History (mocadinha) -->
		<div class="mt-auto pt-4 border-t border-gb-bg-soft shrink-0 flex justify-end">
			<button 
				onclick={clearCache}
				style="color: #a89984; opacity: 0.5; font-family: monospace; font-size: 10px; background: transparent; border: none; cursor: pointer; "
				onmouseover={(e) => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.color = '#fb4934'; }}
				onmouseout={(e) => { e.currentTarget.style.opacity = '0.5'; e.currentTarget.style.color = '#a89984'; }}
				title="Limpar cache de vagas já processadas"
			>
				[ purge history ]
			</button>
		</div>
	</div>

	<!-- Right Pane: Output -->
	<div class="flex flex-col w-1/2 p-8 overflow-hidden bg-gb-bg/50 relative">
		{#if currentMode === 'single'}
			<!-- SINGLE MODE OUTPUT -->
			<header class="mb-4 flex justify-between items-center shrink-0 p-4 border border-gb-bg-soft bg-gb-bg">
				<div>
					<h2 class="text-sm font-sans font-bold text-gb-fg uppercase tracking-wider">Analysis Orchestration</h2>
					<p class="font-mono text-[10px] text-gb-gray mt-1">Single Execution Monitoring</p>
				</div>
				<div class="flex items-center gap-2 border border-gb-bg-soft px-3 py-1 bg-gb-bg-soft">
					<span class="w-2 h-2 rounded-full {isRunning ? 'bg-gb-yellow' : 'bg-gb-green'}"></span>
					<span class="text-gb-fg font-mono text-[10px] uppercase tracking-wider">{isRunning ? 'RUNNING' : 'IDLE'}</span>
				</div>
			</header>

			{#if matchData}
				<div class="mb-4 border border-gb-bg-soft bg-gb-bg flex flex-col shrink-0">
					<div class="p-3 bg-gb-bg-soft flex items-center justify-between border-b border-gb-bg">
						<span class="font-mono text-[10px] text-gb-gray uppercase tracking-wider">Match Metrics</span>
						<span class="font-mono font-bold text-xs {matchData.matchScore >= 80 ? 'text-gb-green' : matchData.matchScore >= 50 ? 'text-gb-yellow' : 'text-gb-red'}">
							SCORE: {matchData.matchScore}%
						</span>
					</div>
					{#if matchData.gaps && matchData.gaps.length > 0}
						<div class="p-4">
							<span class="text-gb-gray font-mono text-[10px] uppercase block mb-2">Identified Gaps</span>
							<div class="flex flex-wrap gap-2">
								{#each matchData.gaps as gap}
									<span class="px-2 py-1 text-[10px] font-mono border border-gb-orange text-gb-orange bg-gb-orange/10">
										{gap.keyword}
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}

			<div class="p-2 bg-gb-bg-soft border border-gb-bg-soft shrink-0 flex justify-between items-center mb-1">
				<span class="font-mono text-[10px] text-gb-gray uppercase">System Terminal</span>
			</div>
			
			<div 
				bind:this={singleConsoleElement}
				class="flex-1 overflow-auto bg-gb-bg border border-gb-bg-soft p-4 font-mono text-xs text-gb-gray whitespace-pre-wrap leading-relaxed shadow-inner"
			>
				{#if !consoleOutput}
					<span class="opacity-50">Waiting for input...</span>
				{:else}
					{consoleOutput}
				{/if}
			</div>

			{#if pdfReady}
				<div class="mt-4 shrink-0">
					<a 
						href={`/api/download?path=${encodeURIComponent(pdfPath)}`}
						download="resume.pdf"
						class="block text-center w-full py-3 font-sans font-bold text-gb-bg bg-gb-green hover:bg-[#98971a] uppercase tracking-widest text-xs cursor-pointer"
					>
						[ Download PDF Artifact ]
					</a>
				</div>
			{/if}

			{#if awaitingConfirmation}
				<div class="mt-4 shrink-0 p-4 border border-gb-blue bg-gb-bg-soft flex items-center justify-between">
					<div class="flex items-center gap-3">
						<span class="w-2 h-2 rounded-full bg-gb-blue"></span>
						<div>
							<span class="block font-sans font-bold text-gb-blue uppercase tracking-widest text-xs">Action Required</span>
							<span class="text-gb-gray font-mono text-[10px] mt-1 block">Form auto-filled. Send application?</span>
						</div>
					</div>
					<button 
						onclick={confirmApply}
						class="px-6 py-2 font-sans font-bold text-gb-bg bg-gb-blue hover:bg-[#458588] uppercase tracking-widest text-xs cursor-pointer"
					>
						Confirm
					</button>
				</div>
			{/if}

		{:else}
			<!-- BATCH MODE OUTPUT -->
			<header class="mb-4 flex justify-between items-center shrink-0 p-4 border border-gb-bg-soft bg-gb-bg">
				<div>
					<h2 class="text-sm font-sans font-bold text-gb-fg uppercase tracking-wider">Pipeline Orchestration</h2>
					<p class="font-mono text-[10px] text-gb-gray mt-1">Batch Execution Monitoring</p>
				</div>
				<div class="flex items-center gap-2 border border-gb-bg-soft px-3 py-1 bg-gb-bg-soft">
					<span class="w-2 h-2 rounded-full {isBatchRunning ? 'bg-gb-yellow' : 'bg-gb-green'}"></span>
					<span class="text-gb-fg font-mono text-[10px] uppercase tracking-wider">{isBatchRunning ? 'RUNNING' : 'IDLE'}</span>
				</div>
			</header>

			<div class="flex-1 overflow-auto min-h-[40%] bg-gb-bg border border-gb-bg-soft mb-4">
				{#if !batchStatusData || !batchStatusData.jobs || Object.keys(batchStatusData.jobs).length === 0}
					<div class="h-full flex items-center justify-center text-gb-gray font-mono text-[10px] uppercase tracking-widest">
						No active deployments
					</div>
				{:else}
					<table class="w-full text-left font-mono text-xs">
						<thead class="sticky top-0 bg-gb-bg-soft text-gb-gray uppercase text-[10px] border-b border-gb-bg">
							<tr>
								<th class="p-3 w-24">Status</th>
								<th class="p-3">Job Name</th>
								<th class="p-3 text-right">Artifact</th>
							</tr>
						</thead>
						<tbody>
							{#each Object.entries(batchStatusData.jobs).filter(([id, j]) => j.status !== 'pending') as [id, statusJob]: [string, any] (id)}
								<tr class="border-b border-gb-bg-soft hover:bg-gb-bg-soft">
									<td class="p-3">
										<span class="px-2 py-1 text-[9px] uppercase tracking-widest border
											{statusJob.status === 'completed' ? 'border-gb-green text-gb-green' :
											 statusJob.status === 'ignored' ? 'border-gb-gray text-gb-gray' :
											 statusJob.status === 'failed' ? 'border-gb-red text-gb-red' :
											 statusJob.status === 'scraping' || statusJob.status === 'generating' ? 'border-gb-yellow text-gb-yellow' :
											 'border-gb-gray text-gb-gray'}"
										>
											{statusJob.status === 'ignored' ? 'SKIPPED' : statusJob.status === 'scraping' || statusJob.status === 'generating' ? 'BUILDING' : statusJob.status}
										</span>
									</td>
									<td class="p-3">
										<div class="font-bold text-gb-fg truncate max-w-[200px]">
											<a href={statusJob.url} target="_blank" rel="noopener noreferrer" class="hover:underline hover:text-gb-yellow">
												{statusJob.title}
											</a>
										</div>
										<div class="text-[10px] text-gb-gray mt-1 truncate">{statusJob.company}</div>
										{#if statusJob.error}
											<div class="text-[10px] text-gb-red mt-2 p-2 bg-gb-red/10 border border-gb-red/30 whitespace-pre-wrap">{statusJob.error}</div>
										{/if}
									</td>
									<td class="p-3 text-right align-top">
										{#if statusJob.status === 'completed' && statusJob.pdf_path}
											<a href={`/api/download?path=${encodeURIComponent(statusJob.pdf_path)}`} download class="text-[10px] font-bold text-gb-green border border-gb-green px-3 py-1 hover:bg-gb-green hover:text-gb-bg uppercase">
												[ Download PDF ]
											</a>
										{:else}
											<span class="text-gb-gray opacity-50 text-[10px]">-</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</div>
			
			<div class="p-2 bg-gb-bg-soft border border-gb-bg-soft shrink-0 flex justify-between items-center mb-1">
				<span class="font-mono text-[10px] text-gb-gray uppercase">System Terminal</span>
			</div>

			<!-- BATCH CONSOLE OUTPUT -->
			<div 
				bind:this={batchConsoleElement}
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
