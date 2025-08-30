import{U as n,A as d,D as u,R as h}from"./RealtimeService.DF0WN3ki.js";(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))s(a);new MutationObserver(a=>{for(const o of a)if(o.type==="childList")for(const r of o.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&s(r)}).observe(document,{childList:!0,subtree:!0});function t(a){const o={};return a.integrity&&(o.integrity=a.integrity),a.referrerPolicy&&(o.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?o.credentials="include":a.crossOrigin==="anonymous"?o.credentials="omit":o.credentials="same-origin",o}function s(a){if(a.ep)return;a.ep=!0;const o=t(a);fetch(a.href,o)}})();class I extends EventTarget{constructor(){super(),this.routes=new Map,this.currentRoute=null,this.currentParams={},this.isInitialized=!1,this.basePath=""}init(){this.isInitialized||(window.addEventListener("popstate",e=>{this.handleLocationChange()}),this.handleLocationChange(),this.isInitialized=!0)}addRoute(e,t,s={}){const a=this.pathToRegex(e);this.routes.set(e,{pattern:a,handler:t,params:this.extractParams(e),title:s.title||"StreamGank",requiresAuth:s.requiresAuth||!1,metadata:s.metadata||{}}),console.log(`🛤️ Route registered: ${e}`)}navigate(e,t={}){const{replace:s=!1,state:a=null}=t;s?window.history.replaceState(a,"",e):window.history.pushState(a,"",e),this.handleLocationChange()}back(){window.history.back()}forward(){window.history.forward()}handleLocationChange(){const e=window.location.pathname,t=this.matchRoute(e);if(t){const{route:s,params:a,routeKey:o}=t,r=this.currentRoute;this.currentRoute=o,this.currentParams=a,s.title&&(document.title=s.title),this.dispatchEvent(new CustomEvent("routeChange",{detail:{path:e,route:o,params:a,previousRoute:r,metadata:s.metadata}}));try{s.handler(a,e),console.log(`🛤️ Navigated to: ${e} (${o})`)}catch(i){console.error("🛤️ Route handler error:",i),this.dispatchEvent(new CustomEvent("routeError",{detail:{path:e,error:i}}))}}else this.handle404(e)}matchRoute(e){for(const[t,s]of this.routes.entries()){const a=e.match(s.pattern);if(a){const o={};return s.params.forEach((r,i)=>{o[r]=a[i+1]}),{route:s,params:o,routeKey:t,match:a}}}return null}pathToRegex(e){const t=e.replace(/[.*+?^${}()|[\]\\]/g,"\\$&").replace(/\\:([^/]+)/g,"([^/]+)");return new RegExp(`^${t}$`)}extractParams(e){const t=[],s=e.matchAll(/:([^/]+)/g);for(const a of s)t.push(a[1]);return t}handle404(e){console.warn(`🛤️ No route found for: ${e}`),this.dispatchEvent(new CustomEvent("notFound",{detail:{path:e}})),e!=="/"&&e!=="/dashboard"&&this.navigate("/dashboard",{replace:!0})}generateUrl(e,t={}){let s=e;for(const[a,o]of Object.entries(t))s=s.replace(`:${a}`,encodeURIComponent(o));return s}getCurrentRoute(){return{path:window.location.pathname,route:this.currentRoute,params:this.currentParams,hash:window.location.hash,search:window.location.search}}isCurrentRoute(e){return this.currentRoute===e}updateQuery(e){const t=new URL(window.location);for(const[s,a]of Object.entries(e))a==null?t.searchParams.delete(s):t.searchParams.set(s,a);this.navigate(t.pathname+t.search,{replace:!0})}getQuery(){const e={},t=new URLSearchParams(window.location.search);for(const[s,a]of t.entries())e[s]=a;return e}cleanup(){window.removeEventListener("popstate",this.handleLocationChange),this.routes.clear(),this.isInitialized=!1,console.log("🛤️ Router cleaned up")}emit(e,t){const s=new CustomEvent(e,{detail:t});this.dispatchEvent(s)}}const m=new I;class T extends EventTarget{constructor(){super(),this.activeJobs=new Map,this.jobHistory=new Map,this.currentJob=null,this.maxJobHistory=100,this.monitoringInterval=5e3,this.monitoringTimer=null,this.isGenerationActive=!1,this.creatomateMessages=new Set}init(){this.setupEventListeners()}setupEventListeners(){window.addEventListener("beforeunload",()=>{this.cleanup()})}async startVideoGeneration(e){try{if(this.validateGenerationParams(e),this.isGenerationActive)throw new Error("Another video generation is already in progress");this.isGenerationActive=!0,n.showProgress(),n.disableGenerateButton("Starting generation..."),n.addStatusMessage("info","🚀","Starting video generation..."),this.creatomateMessages.clear();const t=await d.generateVideo(e);if(!t.success)throw new Error(t.message||"Failed to start video generation");const s=this.createJobObject(t,e);return this.activeJobs.set(s.id,s),this.currentJob=s,this.startJobMonitoring(s.id),n.addStatusMessage("success","✅",`Job queued successfully! ${s.queuePosition?`Position: ${s.queuePosition}`:""}`),n.updateProgress(5,"Job queued, waiting to start..."),this.dispatchEvent(new CustomEvent("jobStarted",{detail:{job:s}})),console.log(`💼 Job started: ${s.id}`),{success:!0,job:s}}catch(t){throw console.error("❌ Failed to start video generation:",t),this.resetGenerationState(),n.addStatusMessage("error","❌",`Failed to start generation: ${t.message}`),this.dispatchEvent(new CustomEvent("jobError",{detail:{error:t}})),t}}createJobObject(e,t){return{id:e.jobId,params:t,status:"pending",progress:0,createdAt:new Date().toISOString(),startedAt:null,completedAt:null,queuePosition:e.queuePosition||0,error:null,result:null,creatomateId:null,videoUrl:null}}validateGenerationParams(e){const s=["country","platform","genre","contentType"].filter(a=>!e[a]);if(s.length>0)throw new Error(`Missing required parameters: ${s.join(", ")}`);console.log("✅ Parameters validated:",e)}async startJobMonitoring(e){this.monitoringTimer&&clearInterval(this.monitoringTimer),console.log(`👀 Started monitoring job: ${e}`),this.monitoringTimer=setInterval(async()=>{try{await this.updateJobStatus(e)}catch(t){console.error("❌ Job monitoring error:",t),this.consecutiveErrors>3&&(this.stopJobMonitoring(),n.addStatusMessage("warning","⚠️","Job monitoring stopped due to repeated errors"))}},this.monitoringInterval)}stopJobMonitoring(){this.monitoringTimer&&(clearInterval(this.monitoringTimer),this.monitoringTimer=null,console.log("⏹️ Job monitoring stopped"))}async updateJobStatus(e){if(this.activeJobs.get(e))try{const s=await d.getJobStatus(e);s.success&&s.job&&this.processJobUpdate(s.job)}catch(s){throw console.error(`❌ Failed to update job status for ${e}:`,s),s}}processJobUpdate(e){const t=this.activeJobs.get(e.id);if(!t)return;const s=t.status,a=t.progress;Object.assign(t,{status:e.status,progress:e.progress||0,currentStep:e.currentStep,startedAt:e.startedAt||t.startedAt,completedAt:e.completedAt,error:e.error,result:e,creatomateId:e.creatomateId,videoUrl:e.videoUrl}),s!==t.status&&this.handleJobStatusChange(t,s),a!==t.progress&&this.updateJobProgress(t),t.creatomateId&&!t.videoUrl&&t.status==="completed"&&this.startCreatomateMonitoring(t),this.dispatchEvent(new CustomEvent("jobUpdated",{detail:{job:t,previousStatus:s}})),console.log(`💼 Job ${t.id} updated: ${t.status} (${t.progress}%)`)}handleJobStatusChange(e,t){switch(e.status){case"processing":t==="pending"&&(n.addStatusMessage("info","⚡","Job started processing!"),e.startedAt=new Date().toISOString());break;case"completed":this.handleJobCompletion(e);break;case"failed":this.handleJobFailure(e);break;case"cancelled":this.handleJobCancellation(e);break}}handleJobCompletion(e){console.log(`✅ Job completed: ${e.id}`),e.videoUrl?this.finishSuccessfulGeneration(e):e.creatomateId?(n.updateProgress(90,"Python script completed, video rendering..."),n.addStatusMessage("info","🎬",`Video rendering started (ID: ${e.creatomateId}). Monitoring progress...`),this.startCreatomateMonitoring(e)):(n.addStatusMessage("warning","⚠️","Job completed but video URL not yet available"),this.moveJobToHistory(e)),this.dispatchEvent(new CustomEvent("jobCompleted",{detail:{job:e}}))}startCreatomateMonitoring(e){let t=0;const s=40,a=async()=>{t++;try{const o=await d.getCreatomateStatus(e.creatomateId);if(o.success&&o.videoUrl)e.videoUrl=o.videoUrl,e.result.videoUrl=o.videoUrl,this.finishSuccessfulGeneration(e);else if(o.success&&o.status){const r=o.status.toLowerCase(),i=r.charAt(0).toUpperCase()+r.slice(1);if(t%4===0){const g=`rendering-update-${Math.floor(t/4)}`;this.creatomateMessages.has(g)||(n.addStatusMessage("info","⏳",`Video status: ${i}... (${t}/${s})`),this.creatomateMessages.add(g))}let c=90+t/s*10;(r.includes("render")||r.includes("process"))&&(c=Math.min(95,c)),n.updateProgress(c,`Rendering: ${i}`),t<s?setTimeout(()=>a(),3e4):this.handleCreatomateTimeout(e)}else this.handleCreatomateError(e,o.message,t,s,a)}catch(o){this.handleCreatomateNetworkError(e,o,t,s,a)}};a()}handleCreatomateTimeout(e){const t="creatomate-timeout";this.creatomateMessages.has(t)||(n.addStatusMessage("warning","⚠️",'Video rendering is taking longer than expected. Use "Check Status" to monitor manually.'),this.creatomateMessages.add(t)),n.enableGenerateButton(),this.isGenerationActive=!1}handleCreatomateError(e,t,s,a,o){const r=`creatomate-error-${t}`;this.creatomateMessages.has(r)||(n.addStatusMessage("error","❌",`Render status check failed: ${t||"Unknown error"}`),this.creatomateMessages.add(r)),s<a?setTimeout(()=>o(),3e4):(n.addStatusMessage("error","❌","Unable to check render status after multiple attempts."),this.moveJobToHistory(e))}handleCreatomateNetworkError(e,t,s,a,o){console.error("Creatomate status check error:",t);const r=`network-error-${s}`;s%3===0&&!this.creatomateMessages.has(r)&&(n.addStatusMessage("warning","⚠️",`Network error checking render status (attempt ${s})`),this.creatomateMessages.add(r)),s<a?setTimeout(()=>o(),3e4):(n.addStatusMessage("error","❌","Network errors prevented render status monitoring."),this.moveJobToHistory(e))}finishSuccessfulGeneration(e){n.updateProgress(100,"Generation completed!"),n.addStatusMessage("success","🎉","Video generation completed successfully!"),n.displayVideo({jobId:e.id,videoUrl:e.videoUrl,creatomateId:e.creatomateId,timestamp:new Date().toLocaleString()}),this.moveJobToHistory(e),this.resetGenerationState()}handleJobFailure(e){console.error(`❌ Job failed: ${e.id}`,e.error),n.updateProgress(0,"Generation failed"),n.addStatusMessage("error","❌",`Generation failed: ${e.error||"Unknown error"}`,!1),this.moveJobToHistory(e),this.dispatchEvent(new CustomEvent("jobFailed",{detail:{job:e}})),this.resetGenerationState()}handleJobCancellation(e){console.log(`⏹️ Job cancelled: ${e.id}`),n.addStatusMessage("warning","⏹️","Job was cancelled"),this.moveJobToHistory(e),this.dispatchEvent(new CustomEvent("jobCancelled",{detail:{job:e}})),this.resetGenerationState()}updateJobProgress(e){e===this.currentJob&&n.updateProgress(e.progress,e.currentStep||"Processing...")}resetGenerationState(){n.hideProgress(),n.enableGenerateButton(),this.isGenerationActive=!1,this.stopJobMonitoring()}async cancelJob(e){try{const t=await d.cancelJob(e);if(t.success)return n.addStatusMessage("info","⏹️","Job cancellation requested"),!0;throw new Error(t.message||"Failed to cancel job")}catch(t){return console.error("❌ Failed to cancel job:",t),n.addStatusMessage("error","❌",`Failed to cancel job: ${t.message}`),!1}}stopVideoGeneration(){this.currentJob&&this.cancelJob(this.currentJob.id),this.resetGenerationState(),n.addStatusMessage("warning","⏹️","Video generation stopped")}moveJobToHistory(e){this.activeJobs.delete(e.id),this.jobHistory.set(e.id,{...e,movedToHistoryAt:new Date().toISOString()}),this.currentJob&&this.currentJob.id===e.id&&(this.currentJob=null),this.limitJobHistory()}limitJobHistory(){if(this.jobHistory.size>this.maxJobHistory){const e=Array.from(this.jobHistory.entries()),t=e.slice(0,e.length-this.maxJobHistory);t.forEach(([s])=>{this.jobHistory.delete(s)}),console.log(`🧹 Cleaned up ${t.length} old job records`)}}getJob(e){return this.activeJobs.get(e)||this.jobHistory.get(e)||null}getActiveJobs(){return Array.from(this.activeJobs.values())}getJobStats(){var e;return{active:this.activeJobs.size,history:this.jobHistory.size,total:this.activeJobs.size+this.jobHistory.size,currentJob:((e=this.currentJob)==null?void 0:e.id)||null,isMonitoring:!!this.monitoringTimer,isGenerationActive:this.isGenerationActive}}cleanup(){this.stopJobMonitoring(),console.log("🧹 Job Manager cleaned up")}}const p=new T;class D{constructor(){this.genresByCountry={},this.templatesByGenre={},this.platformsByCountry={},this.formState={country:"",platform:"",platforms:[],genre:"",genres:[],template:"",contentType:""},this.isValidating=!1,this.validationCache=new Map,this.isInitialized=!1}async init(){if(this.isInitialized){console.log("📋 FormManager already initialized, skipping...");return}await this.loadFormConfiguration(),this.setupEventListeners(),this.initializeFormState(),this.isInitialized=!0,console.log("✅ FormManager initialized successfully")}async loadFormConfiguration(){this.loadGenresByCountry(),this.loadTemplatesByGenre(),await this.initializePlatformData()}loadGenresByCountry(){this.genresByCountry={FR:{"Action & Aventure":"Action & Adventure",Animation:"Animation","Crime & Thriller":"Crime & Thriller",Documentaire:"Documentary",Drame:"Drama",Fantastique:"Fantasy","Film de guerre":"War Movies",Histoire:"History",Horreur:"Horror","Musique & Musicale":"Music & Musical","Mystère & Thriller":"Mystery & Thriller","Pour enfants":"Kids","Reality TV":"Reality TV","Réalisé en Europe":"Made in Europe","Science-Fiction":"Science Fiction","Sport & Fitness":"Sport & Fitness",Western:"Western"},US:{"Action & Adventure":"Action & Adventure",Animation:"Animation",Crime:"Crime",Documentary:"Documentary",Drama:"Drama",Fantasy:"Fantasy",History:"History",Horror:"Horror","Kids & Family":"Kids & Family","Made in Europe":"Made in Europe","Music & Musical":"Music & Musical","Mystery & Thriller":"Mystery & Thriller","Reality TV":"Reality TV","Romance Movies":"Romance Movies","Science Fiction":"Science Fiction","Sport & Fitness":"Sport & Fitness",Western:"Western"}}}loadTemplatesByGenre(){this.templatesByGenre={Horror:"ed21a309a5c84b0d873fde68642adea3",Horreur:"ed21a309a5c84b0d873fde68642adea3","Action & Adventure":"7f8db20ddcd94a33a1235599aa8bf473","Action & Aventure":"7f8db20ddcd94a33a1235599aa8bf473",default:"cc6718c5363e42b282a123f99b94b335"}}async initializePlatformData(){const e=document.getElementById("country");if(e){const s=e.value||"US";await this.updatePlatformDropdown(s)}const t=e?e.value:"US";await this.updateGenreDropdown(t),this.updateTemplateDropdown(),this.setDefaultSelections(),this.refreshFormState(),this.disableGenerateButton(),console.log("✅ Platform data initialization complete")}async updatePlatformDropdown(e){const t=`platforms_${e}`;if(!this.validationCache.has(t))try{const s=await d.get(`/api/platforms/${e}`);s.success&&s.platforms?(this.populatePlatformSelect(s.platforms),this.validationCache.set(t,!0),console.log("✅ Platform dropdown update completed")):console.error("❌ Invalid platform API response:",s)}catch(s){console.error("❌ Failed to load platforms:",s)}}async updateGenreDropdown(e){const t=`genres_${e}`;if(this.validationCache.has(t)){console.log(`📋 Using cached genres for ${e}`);return}try{console.log(`📋 Loading genres for ${e}...`);const s=await d.get(`/api/genres/${e}`);s.success&&s.genres?(console.log(`📋 API returned ${s.genres.length} genres:`,s.genres),this.populateGenreSelect(s.genres),this.validationCache.set(t,!0),console.log("✅ Genre dropdown update completed")):console.error("❌ Invalid genre API response:",s)}catch(s){console.error("❌ Failed to load genres:",s)}}updateTemplateDropdown(){const e=document.getElementById("template");if(!e)return;e.innerHTML='<option value="">Select Template...</option>',[{value:"cc6718c5363e42b282a123f99b94b335",text:"Default Template"},{value:"ed21a309a5c84b0d873fde68642adea3",text:"Horror/Thriller Cinematic"},{value:"e44b139a1b94446a997a7f2ac5ac4178",text:"Action Adventure"}].forEach(s=>{const a=document.createElement("option");a.value=s.value,a.textContent=s.text,e.appendChild(a)}),e.value="cc6718c5363e42b282a123f99b94b335"}setupEventListeners(){if(this.eventListenersSetup)return;const e=document.getElementById("country");e&&e.addEventListener("change",i=>{this.handleCountryChange(i.target.value)});const t=document.getElementById("platform");t&&t.addEventListener("change",i=>{this.handlePlatformChange(i.target.value)});const s=document.getElementById("template");s&&s.addEventListener("change",i=>{this.handleTemplateChange(i.target.value)});const a=document.getElementById("refresh-preview-btn");a&&a.addEventListener("click",()=>{this.loadMoviePreview()});const o=document.querySelectorAll('input[name="contentType"]');o&&Array.from(o).forEach(i=>{i.addEventListener("change",c=>{c.target.checked&&this.handleContentTypeChange(c.target.value)})});const r=document.getElementById("generate-video");r&&r.addEventListener("click",i=>{i.preventDefault(),this.handleFormSubmit()}),this.eventListenersSetup=!0}initializeFormState(){const e=document.getElementById("country");e&&!e.value&&(e.value="US"),this.ensureContentTypeSelected(),console.log("📋 Form state initialization complete")}ensureContentTypeSelected(){const e=document.querySelectorAll('input[name="contentType"]'),t=Array.from(e).find(s=>s.checked);if(console.log("📋 Content Type Radios found:",e.length),console.log("📋 Already checked:",t?t.value:"none"),!t&&e.length>0){const s=Array.from(e).find(a=>a.value==="Serie");s?(s.checked=!0,console.log("📋 Force-selected Serie (TV Shows) radio button")):(e[0].checked=!0,console.log("📋 Force-selected first radio button:",e[0].value))}}refreshFormState(){const e=u.getFormData();Object.assign(this.formState,e),console.log("📋 Form state updated"),console.log("📋 Final form data:",this.formState),this.updatePreviewWithMovies()}setDefaultSelections(){let e=!1;const t=document.getElementById("platform");if(t&&t.children.length>1&&t.selectedIndex===0){let a=-1;for(let o=1;o<t.options.length;o++)if(t.options[o].value.toLowerCase().includes("netflix")){a=o;break}t.selectedIndex=a>0?a:1,this.formState.platform=t.value,console.log("📋 Set default platform:",this.formState.platform),e=!0}const s=document.getElementById("genre");if(s&&s.children.length>1&&s.selectedIndex===0){let a=-1;for(let o=1;o<s.options.length;o++)if(s.options[o].value.toLowerCase().includes("horror")){a=o;break}s.selectedIndex=a>0?a:1,this.formState.genre=s.value,console.log("📋 Set default genre:",this.formState.genre),e=!0,this.updateTemplates(this.formState.genre)}e&&console.log("📋 Defaults set")}manualRefresh(){return console.log("📋 Manual form refresh triggered"),this.refreshFormState(),this.formState}async handleCountryChange(e){console.log(`📋 Country changed: ${e}`),this.formState.country=e,this.resetPlatformSelection(),this.resetGenreSelection(),this.resetTemplateSelection(),e&&await this.updatePlatforms(e),this.updatePreview()}async handlePlatformChange(){const e=[];document.querySelectorAll('input[name="platforms"]:checked').forEach(s=>{e.push(s.value)}),console.log("📺 Platform selection changed:",e),this.formState.platforms=e,this.formState.platform=e[0]||"",this.resetGenreSelection(),this.resetTemplateSelection(),this.updatePreviewWithMovies()}handleGenreChange(){const e=[];document.querySelectorAll('input[name="genres"]:checked').forEach(s=>{e.push(s.value)}),console.log("🎭 Genre selection changed:",e),this.formState.genres=e,this.formState.genre=e[0]||"",this.resetTemplateSelection(),e.length>0&&this.updateTemplates(e[0]),this.updatePreviewWithMovies()}handleTemplateChange(e){console.log(`📋 Template changed: ${e}`),this.formState.template=e,this.updatePreview()}handleContentTypeChange(e){console.log(`📋 Content type changed: ${e}`),this.formState.contentType=e,this.updatePreviewWithMovies()}async updatePlatforms(e){try{const t=await d.getPlatforms(e);t.success&&t.platforms?this.populatePlatformSelect(t.platforms):this.populateDefaultPlatforms(e)}catch(t){console.error("❌ Failed to load platforms:",t),this.populateDefaultPlatforms(e)}}populatePlatformSelect(e){const t=document.getElementById("platform-checkboxes");if(!t){console.error("❌ Platform checkboxes container not found!");return}console.log("📋 Populating platforms:",e),t.innerHTML="",e.forEach((s,a)=>{const o=document.createElement("div");o.className="checkbox-item";const r=document.createElement("input");r.type="checkbox",r.id=`platform-${a}`,r.value=s,r.name="platforms",s.toLowerCase().includes("netflix")&&(r.checked=!0,this.formState.platforms=[s]);const i=document.createElement("label");i.htmlFor=`platform-${a}`,i.textContent=s,r.addEventListener("change",c=>{this.handlePlatformChange()}),o.appendChild(r),o.appendChild(i),t.appendChild(o)}),console.log("✅ Platform checkboxes populated with",e.length,"options")}populateDefaultPlatforms(e){const t=[{value:"Netflix",name:"Netflix"},{value:"Prime Video",name:"Prime Video"},{value:"Disney+",name:"Disney+"},{value:"Apple TV+",name:"Apple TV+"},{value:"HBO Max",name:"HBO Max"}];this.populatePlatformSelect(t)}async updateGenres(e,t=null){const s=`genres_${e}`;if(this.validationCache.has(s)){console.log(`📋 Using cached genres for ${e}`);return}try{console.log(`📋 Loading genres for ${e}...`);const a=await d.getGenres(e);if(a.success&&a.genres){console.log(`📋 API returned ${a.genres.length} genres for ${e}:`,a.genres),this.populateGenreSelect(a.genres),this.validationCache.set(s,!0);return}}catch(a){console.error("❌ Failed to load genres from API:",a)}console.log(`📋 Using fallback static genres for ${e}`),this.populateGenreSelectFromStatic(e)}populateGenreSelect(e){const t=document.getElementById("genre-checkboxes");if(!t){console.error("❌ Genre checkboxes container not found!");return}console.log("📋 Populating genres:",e),t.innerHTML="",e.forEach((s,a)=>{const o=document.createElement("div");o.className="checkbox-item";const r=document.createElement("input");r.type="checkbox",r.id=`genre-${a}`,r.value=s,r.name="genres",s.toLowerCase().includes("horror")&&(r.checked=!0,this.formState.genres=[s]);const i=document.createElement("label");i.htmlFor=`genre-${a}`,i.textContent=s,r.addEventListener("change",c=>{this.handleGenreChange()}),o.appendChild(r),o.appendChild(i),t.appendChild(o)}),console.log("✅ Genre checkboxes populated with",e.length,"options")}populateGenreSelectFromStatic(e){const t=this.genresByCountry[e];if(!t)return;const s=document.getElementById("genre");if(s){for(;s.children.length>1;)s.removeChild(s.lastChild);Object.entries(t).forEach(([a,o])=>{const r=document.createElement("option");r.value=o,r.textContent=a,s.appendChild(r)})}}updateTemplates(e){const t=document.getElementById("template");if(!t)return;const s=this.getTemplateForGenre(e);Array.from(t.options).forEach(a=>{a.value===s&&(a.selected=!0,this.formState.template=s)}),console.log(`📋 Template auto-selected for genre '${e}': ${s}`)}getTemplateForGenre(e){if(this.templatesByGenre[e])return this.templatesByGenre[e];const t=e.toLowerCase();for(const[s,a]of Object.entries(this.templatesByGenre))if(s.toLowerCase()===t)return a;return this.templatesByGenre.default}resetPlatformSelection(){const e=document.getElementById("platform");if(e)for(e.selectedIndex=0;e.children.length>1;)e.removeChild(e.lastChild);this.formState.platform=""}resetGenreSelection(){const e=document.getElementById("genre");if(e)for(e.selectedIndex=0;e.children.length>1;)e.removeChild(e.lastChild);this.formState.genre=""}resetTemplateSelection(){const e=document.getElementById("template");e&&(e.selectedIndex=0),this.formState.template=""}validateForm(){const e=[],t=[];return this.formState.country||e.push("Country is required"),this.formState.platform||e.push("Platform is required"),this.formState.genre||e.push("Genre is required"),this.formState.contentType||e.push("Content type is required"),this.formState.template||t.push("No template selected - default will be used"),{isValid:e.length===0,errors:e,warnings:t}}async validateStreamGankUrl(e){if(!e||e.includes("Select all parameters"))return{valid:!1,message:"Please complete the form to generate a valid URL"};const t=`url:${e}`;if(this.validationCache.has(t))return this.validationCache.get(t);try{n.addStatusMessage("info","🔍","Validating URL..."),this.isValidating=!0;const s=await d.validateUrl(e),a={valid:s.success,message:s.message,moviesCount:s.moviesCount,timestamp:new Date().toISOString()};return this.validationCache.set(t,a),a.valid?n.addStatusMessage("success","✅",`URL validated! Found ${a.moviesCount} items`):n.addStatusMessage("error","❌",`URL validation failed: ${a.message}`),a}catch(s){console.error("❌ URL validation error:",s);const a={valid:!1,message:s.message||"Validation failed",timestamp:new Date().toISOString()};return n.addStatusMessage("error","❌",`Validation error: ${a.message}`),a}finally{this.isValidating=!1}}async handleFormSubmit(){try{this.updateFormStateFromDOM();const e=this.validateForm();if(!e.isValid){e.errors.forEach(a=>{n.addStatusMessage("error","❌",a)});return}e.warnings.forEach(a=>{n.addStatusMessage("warning","⚠️",a)});const t=this.generateStreamGankUrl(),s=await this.validateStreamGankUrl(t);if(!s.valid)return;document.dispatchEvent(new CustomEvent("formSubmit",{detail:{formData:{...this.formState},previewUrl:t,validation:s}}))}catch(e){console.error("❌ Form submission error:",e),n.addStatusMessage("error","❌",`Form submission failed: ${e.message}`)}}updateFormStateFromDOM(){const e=u.getFormData();Object.assign(this.formState,e)}updatePreview(){n.updateFormPreviewFromState(this.formState),console.log("📋 Preview updated")}updatePreviewWithMovies(){this.updatePreview(),this.loadMoviePreview(),console.log("📋 Preview updated with movie reload")}async loadMoviePreview(){const e=this.formState.country,t=this.formState.platforms||[],s=this.formState.genres||[],a=this.formState.contentType;if(!e||t.length===0||s.length===0){this.hideMoviePreview();return}console.log("🎬 Loading movie preview:",{country:e,platforms:t,genres:s,contentType:a}),this.showMoviePreviewLoading();try{const r=await(await fetch("/api/movies/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({country:e,platforms:t,genre:s,contentType:a==="All"?null:a})})).json();r.success&&r.movies&&r.movies.length>0?this.displayMoviePreview(r.movies):this.showMoviePreviewEmpty()}catch(o){console.error("❌ Failed to load movie preview:",o),this.showMoviePreviewEmpty()}}displayMoviePreview(e){const t=document.getElementById("movie-preview-container"),s=document.getElementById("movie-preview-grid"),a=document.getElementById("movie-preview-loading"),o=document.getElementById("movie-preview-empty");!t||!s||(a.style.display="none",o.style.display="none",s.innerHTML="",e.forEach((r,i)=>{const c=this.createMovieCard(r,i);s.appendChild(c)}),t.style.display="block",this.enableGenerateButton(),console.log(`✅ Displayed ${e.length} movie preview cards`))}createMovieCard(e,t){const s=document.createElement("div");s.className="col-md-4";const a=document.createElement("div");a.className="movie-card";const o=e.poster_url||e.backdrop_url||"https://via.placeholder.com/300x450/333/fff?text=No+Image",r=e.title||"Unknown Title";return a.innerHTML=`
            <img src="${o}" alt="${r}" class="movie-poster" 
                 onerror="this.src='https://via.placeholder.com/300x450/333/fff?text=No+Image'">
            <div class="movie-title-large">${r}</div>
        `,s.appendChild(a),s}showMoviePreviewLoading(){const e=document.getElementById("movie-preview-container"),t=document.getElementById("movie-preview-loading"),s=document.getElementById("movie-preview-grid"),a=document.getElementById("movie-preview-empty");!e||!t||(e.style.display="block",t.style.display="block",s.innerHTML="",a.style.display="none",this.disableGenerateButton())}showMoviePreviewEmpty(){const e=document.getElementById("movie-preview-container"),t=document.getElementById("movie-preview-loading"),s=document.getElementById("movie-preview-grid"),a=document.getElementById("movie-preview-empty");!e||!a||(e.style.display="block",t.style.display="none",s.innerHTML="",a.style.display="block",this.disableGenerateButton())}hideMoviePreview(){const e=document.getElementById("movie-preview-container");e&&(e.style.display="none"),this.disableGenerateButton()}enableGenerateButton(){const e=document.getElementById("generate-video");e&&(e.disabled=!1,e.classList.remove("btn-secondary"),e.classList.add("btn-primary"),e.innerHTML='<span class="icon">🎬</span> Generate Video',console.log("✅ Generate button enabled"))}disableGenerateButton(){const e=document.getElementById("generate-video");e&&(e.disabled=!0,e.classList.remove("btn-primary"),e.classList.add("btn-secondary"),e.innerHTML='<span class="icon">⚠️</span> No Movies Available',console.log("🚫 Generate button disabled"))}generateStreamGankUrl(){if(!this.formState.country||!this.formState.platform||!this.formState.contentType)return"Select all parameters to generate URL";const e="https://streamgank.com",t=new URLSearchParams;if(this.formState.country&&t.set("country",this.formState.country),this.formState.platform&&t.set("platforms",this.formState.platform.toLowerCase()),this.formState.genre&&this.formState.genre!=="all"){const a={Horreur:"Horror","Action & Aventure":"Action",Animation:"Animation"}[this.formState.genre]||this.formState.genre;t.set("genres",a)}if(this.formState.contentType&&this.formState.contentType!=="all"){const a={movies:"Film",series:"Serie",tvshows:"Serie","tv-shows":"Serie"}[this.formState.contentType.toLowerCase()]||this.formState.contentType;t.set("type",a)}return`${e}?${t.toString()}`}getFormData(){return this.updateFormStateFromDOM(),{...this.formState}}setFormData(e){Object.assign(this.formState,e),Object.entries(e).forEach(([t,s])=>{const a=u.get(`${t}Select`)||u.get(t);a&&a.value!==void 0&&(a.value=s)}),this.updatePreview()}resetForm(){this.formState={country:"",platform:"",genre:"",template:"",contentType:""},["country","platform","genre","template"].forEach(t=>{const s=document.getElementById(t);s&&(s.selectedIndex=0)});const e=u.get("contentTypeRadios");e&&Array.from(e).forEach(t=>{t.checked=!1}),this.validationCache.clear(),this.updatePreview(),console.log("📋 Form reset")}getValidationState(){return{isValidating:this.isValidating,cacheSize:this.validationCache.size,lastValidation:null}}emit(e,t){console.log(`📤 FormManager emitting ${e}:`,t);const s=new CustomEvent(e,{detail:t});document.dispatchEvent(s)}}const y=new D;class J{constructor(){this.processData=new Map,this.isInitialized=!1,this.updateInterval=null}async init(){this.isInitialized||(console.log("🔧 ProcessTable initializing..."),await this.loadRecentJobs(),this.setupEventListeners(),this.startPeriodicUpdates(),this.isInitialized=!0,console.log("✅ ProcessTable initialized"))}setupEventListeners(){document.addEventListener("click",e=>{const t=e.target.closest(".btn-view-job");if(t){e.preventDefault();const s=t.dataset.jobId;console.log(`🎯 View button clicked for job: ${s}`),this.viewJob(s)}}),document.addEventListener("click",e=>{const t=e.target.closest(".btn-cancel-job");if(t){e.preventDefault();const s=t.dataset.jobId;console.log(`🚫 Cancel button clicked for job: ${s}`),this.cancelJob(s)}}),document.addEventListener("click",e=>{const t=e.target.closest(".btn-delete-job");if(t){e.preventDefault();const s=t.dataset.jobId;console.log(`🗑️ Delete button clicked for job: ${s}`),this.deleteJob(s)}})}async loadRecentJobs(){if(document.hidden){console.log("📋 ProcessTable: Skipping job load - page not visible (anti-spam)");return}try{console.log("📋 ProcessTable: Loading jobs from /api/queue/jobs...");const e=await d.get("/api/queue/jobs");console.log("📋 ProcessTable: API response:",e),e.success&&e.jobs?(console.log(`📋 ProcessTable: Received ${e.jobs.length} jobs`),console.log("📋 ProcessTable: Raw job data:",e.jobs[0]),this.processData.clear(),e.jobs.forEach(t=>{var a,o,r,i;console.log("📋 Processing job:",t);const s={id:t.id,status:t.status||"pending",country:((a=t.parameters)==null?void 0:a.country)||t.country||"Unknown",platform:((o=t.parameters)==null?void 0:o.platform)||t.platform||"Unknown",genre:((r=t.parameters)==null?void 0:r.genre)||t.genre||"Unknown",contentType:((i=t.parameters)==null?void 0:i.contentType)||t.contentType||"Unknown",createdAt:t.createdAt||new Date().toISOString(),startedAt:t.startedAt,completedAt:t.completedAt,failedAt:t.failedAt,progress:t.progress||0,workerId:t.workerId,error:t.error};console.log("📋 Processed job data:",s),this.processData.set(t.id,s)}),console.log(`📋 Loaded ${e.jobs.length} jobs into process table`),this.updateProcessTable()):(console.log("📋 ProcessTable: No jobs received or API failed"),this.updateProcessTable())}catch(e){console.error("❌ Failed to load recent jobs:",e),n.addStatusMessage("error","❌","Failed to load job history"),this.updateProcessTable()}}updateProcessTable(){const e=document.getElementById("job-cards-container"),t=document.getElementById("empty-jobs-state"),s=document.getElementById("jobs-loading-state"),a=document.getElementById("job-count-badge");if(console.log("📊 JobDashboard: Updating dashboard..."),console.log("📊 JobDashboard: Cards container found:",!!e),console.log("📊 JobDashboard: Empty state found:",!!t),!e){console.warn("⚠️ Job cards container not found");return}if(s&&(s.style.display="none"),e.innerHTML="",console.log(`📊 JobDashboard: Processing ${this.processData.size} jobs`),a&&(a.textContent=this.processData.size),this.processData.size===0){t&&(t.style.display="block",console.log("📊 JobDashboard: Showing empty state"));return}t&&(t.style.display="none");const o=Array.from(this.processData.values()).sort((r,i)=>new Date(i.createdAt)-new Date(r.createdAt));o.forEach(r=>{const i=this.createJobCard(r);e.appendChild(i)}),console.log(`📊 JobDashboard: Updated with ${o.length} job cards`)}createJobCard(e){const t=document.createElement("div");t.className="col-lg-6 col-xl-4",this.getStatusClass(e.status);const s=this.getStatusIcon(e.status),a=e.id?e.id.slice(-8):"Unknown";let o="Not started",r="Not started",i="text-muted";if(e.startedAt){const S=new Date(e.startedAt);r=S.toLocaleString();const k=e.completedAt||e.failedAt||new Date,C=new Date(k)-S,$=Math.floor(C/6e4),E=Math.floor(C%6e4/1e3);$>0?o=`${$}m ${E}s`:o=`${E}s`,i="text-info"}else e.createdAt&&(r=`Created: ${new Date(e.createdAt).toLocaleString()}`,i="text-warning");const c=e.progress||0,g=c>=100?"bg-success":c>=50?"bg-info":"bg-warning";let f="border-secondary",b="bg-secondary";switch(e.status){case"pending":f="border-warning",b="bg-warning";break;case"active":case"processing":f="border-info",b="bg-info";break;case"completed":f="border-success",b="bg-success";break;case"failed":f="border-danger",b="bg-danger";break;case"cancelled":f="border-dark",b="bg-dark";break}return t.innerHTML=`
            <div class="card bg-dark ${f} h-100" style="border-radius: 12px; border-width: 2px;">
                <!-- Card Header -->
                <div class="card-header ${b} text-white d-flex justify-content-between align-items-center" style="border-radius: 10px 10px 0 0;">
                    <div class="d-flex align-items-center">
                        <span class="me-2" style="font-size: 1.2em;">${s}</span>
                        <div>
                            <h6 class="mb-0">Job ${a}</h6>
                            <small style="opacity: 0.9;">${e.status.charAt(0).toUpperCase()+e.status.slice(1)}</small>
                        </div>
                    </div>
                    <div class="text-end">
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-outline-light btn-view-job" 
                                    data-job-id="${e.id}" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            ${e.status==="pending"||e.status==="active"?`
                            <button class="btn btn-sm btn-outline-light btn-cancel-job" 
                                    data-job-id="${e.id}" title="Cancel Job">
                                <i class="fas fa-times"></i>
                            </button>
                            `:""}
                            ${e.status==="failed"||e.status==="completed"||e.status==="cancelled"?`
                            <button class="btn btn-sm btn-danger btn-delete-job" 
                                    data-job-id="${e.id}" title="Delete Job Permanently"
                                    style="border: 1px solid #dc3545; background-color: #dc3545; color: white;">
                                <i class="fas fa-trash"></i>
                            </button>
                            `:""}
                        </div>
                    </div>
                </div>

                <!-- Card Body -->
                <div class="card-body">
                    <!-- Progress Section -->
                    <div class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <small class="text-light fw-bold">Progress</small>
                            <small class="text-light">${c}%</small>
                        </div>
                        <div class="progress" style="height: 8px; background-color: #495057; border-radius: 10px;">
                            <div class="progress-bar ${g}" role="progressbar" 
                                 style="width: ${c}%; border-radius: 10px;" 
                                 aria-valuenow="${c}" aria-valuemin="0" aria-valuemax="100">
                            </div>
                        </div>
                        ${e.currentStep?`
                        <small class="text-muted mt-1 d-block" style="font-size: 0.75em;">
                            ${e.currentStep}
                        </small>
                        `:""}
                    </div>

                    <!-- Job Parameters -->
                    <div class="row g-2 mb-3">
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Country</small>
                                <small class="text-light fw-bold">${e.country||"Unknown"}</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Platform</small>
                                <small class="text-info fw-bold">${e.platform||"Unknown"}</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Genre</small>
                                <small class="text-warning fw-bold">${e.genre||"Unknown"}</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="bg-secondary bg-opacity-25 p-2 rounded">
                                <small class="text-muted d-block">Type</small>
                                <small class="text-light fw-bold">${e.contentType||"Unknown"}</small>
                            </div>
                        </div>
                    </div>

                    <!-- Time Information -->
                    <div class="text-center">
                        <small class="${i}">
                            <i class="fas fa-clock me-1"></i>
                            ${r}
                        </small>
                        ${o!=="Not started"?`
                        <br><small class="text-muted">
                            <i class="fas fa-stopwatch me-1"></i>
                            Duration: ${o}
                        </small>
                        `:""}
                        ${e.workerId?`
                        <br><small class="text-muted">
                            <i class="fas fa-user me-1"></i>
                            Worker: ${e.workerId.slice(-8)}
                        </small>
                        `:""}
                    </div>

                    ${e.status==="failed"&&e.error?`
                    <!-- Error Information -->
                    <div class="mt-3 p-2 bg-danger bg-opacity-25 rounded border border-danger">
                        <small class="text-danger fw-bold">
                            <i class="fas fa-exclamation-triangle me-1"></i>
                            Error
                        </small>
                        <small class="text-light d-block mt-1" style="font-size: 0.75em;">
                            ${e.error.length>60?e.error.substring(0,60)+"...":e.error}
                        </small>
                    </div>
                    `:""}
                </div>
            </div>
        `,t}getStatusClass(e){return{pending:"bg-warning",active:"bg-info",completed:"bg-success",failed:"bg-danger",cancelled:"bg-secondary"}[e]||"bg-secondary"}getStatusIcon(e){return{pending:"⏳",active:"⚡",completed:"✅",failed:"❌",cancelled:"🚫"}[e]||"❓"}async viewJob(e){try{console.log(`👁️ Redirecting to job details page: ${e}`),window.location.href=`/job/${e}`}catch(t){console.error("❌ Failed to redirect to job details:",t),n.addStatusMessage("error","❌","Failed to open job details")}}async cancelJob(e){if(confirm(`Cancel job ${e.slice(-8)}?`))try{const t=await d.delete(`/api/queue/job/${e}`);if(t.success){n.addStatusMessage("success","✅","Job cancelled successfully");const s=this.processData.get(e);s&&(s.status="cancelled",this.updateProcessTable())}else throw new Error(t.error||"Failed to cancel job")}catch(t){console.error("❌ Failed to cancel job:",t),n.addStatusMessage("error","❌",`Failed to cancel job: ${t.message}`)}}async deleteJob(e){const t=this.processData.get(e),s=e.slice(-8),a=t?t.status:"Unknown";if(confirm(`⚠️ Permanently delete ${a} job ${s}?

This action cannot be undone!`))try{const o=await d.delete(`/api/queue/job/${e}/delete`);if(o.success)n.addStatusMessage("success","🗑️",`Job ${s} deleted successfully`),this.processData.delete(e),this.updateProcessTable();else throw new Error(o.error||"Failed to delete job")}catch(o){console.error("❌ Failed to delete job:",o),n.addStatusMessage("error","❌",`Failed to delete job: ${o.message}`)}}updateJobStatus(e){const t=this.processData.get(e.id);t&&(Object.assign(t,e),this.updateProcessTable())}addJob(e){this.processData.set(e.id,e),this.updateProcessTable()}startPeriodicUpdates(){this.stopPeriodicUpdates(),this.updateInterval=setInterval(()=>{console.log("📋 ProcessTable: Periodic backup refresh (anti-spam mode)"),this.loadRecentJobs()},6e5),console.log("📋 ProcessTable: Started 10-minute backup polling (anti-spam)")}stopPeriodicUpdates(){this.updateInterval&&(clearInterval(this.updateInterval),this.updateInterval=null)}getProcessData(){return this.processData}cleanup(){this.stopPeriodicUpdates(),this.processData.clear(),this.isInitialized=!1}}const M=new J;window.ProcessTable=M;class A{constructor(){this.currentRoute=null,this.navigationData={brand:{title:"StreamGank",subtitle:"AMBUSH THE BEST VOD TOGETHER",version:"BETA v1.3"},links:[{path:"/dashboard",label:"Dashboard",icon:"📊",description:"Video generation and queue management"},{path:"/jobs",label:"Jobs",icon:"📋",description:"View all jobs and their status"}]}}init(){this.setupRouterListener()}setupRouterListener(){m.addEventListener("routeChange",e=>{this.currentRoute=e.detail.path,this.updateActiveStates()})}render(e={}){const{showBrand:t=!0,showVersion:s=!0,showLogin:a=!0,fixed:o=!1,theme:r="default"}=e;return`
            <nav class="streamgank-navbar ${o?"fixed-top":""} ${r}">
                <div class="container-fluid">
                    <div class="row py-2 align-items-center w-100">
                        <!-- Brand Section -->
                        ${t?this.renderBrand(s):""}
                        
                        <!-- Navigation Links -->
                        <div class="col-auto navigation-links">
                            ${this.renderNavigationLinks()}
                        </div>
                        
                        <!-- Actions Section -->
                        <div class="col-auto ms-auto">
                            <div class="navbar-actions d-flex align-items-center gap-2">
                                ${this.renderStatusIndicator()}
                                ${this.renderQuickActions()}
                                ${a?this.renderLoginButton():""}
                            </div>
                        </div>
                    </div>
                </div>
            </nav>
        `}renderBrand(e){return`
            <div class="col">
                <a href="/dashboard" class="brand-container d-flex align-items-center text-decoration-none">
                    <h1 class="brand-title mb-0">
                        ${this.navigationData.brand.title}
                        <span class="text-accent">Gank</span>
                    </h1>
                    ${e?`
                    <span class="version-badge ms-2">${this.navigationData.brand.version}</span>
                    `:""}
                </a>
                <span class="brand-subtitle d-block">${this.navigationData.brand.subtitle}</span>
            </div>
        `}renderNavigationLinks(){return this.navigationData.links.map(e=>{const t=this.isActiveRoute(e.path);return`
                <a href="${e.path}" 
                   class="nav-link btn ${t?"btn-primary":"btn-outline-primary"} me-2"
                   data-route="${e.path}"
                   title="${e.description}">
                    <span class="nav-icon">${e.icon}</span>
                    <span class="nav-label">${e.label}</span>
                </a>
            `}).join("")}renderStatusIndicator(){return`
            <div class="status-indicator d-none d-md-flex align-items-center me-3">
                <div class="connection-status me-2" id="nav-connection-status">
                    <div class="status-dot bg-success" title="Connected"></div>
                </div>
                <div class="queue-summary" id="nav-queue-summary">
                    <small class="text-muted">
                        Queue: <span id="nav-queue-count" class="badge bg-info">0</span>
                    </small>
                </div>
            </div>
        `}renderQuickActions(){return`
            <div class="quick-actions d-flex gap-1">
                <button class="btn btn-outline-secondary btn-sm" 
                        id="nav-refresh-btn"
                        title="Refresh Status">
                    🔄
                </button>
                <div class="dropdown">
                    <button class="btn btn-outline-secondary btn-sm dropdown-toggle" 
                            type="button" 
                            data-bs-toggle="dropdown">
                        ⚙️
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="toggleQueueDashboard()">Queue Dashboard</a></li>
                        <li><a class="dropdown-item" href="#" onclick="clearAllLogs()">Clear Logs</a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="#" onclick="showAppStatus()">App Status</a></li>
                    </ul>
                </div>
            </div>
        `}renderLoginButton(){return`
            <button class="btn btn-primary login-btn">
                👤 LOGIN
            </button>
        `}isActiveRoute(e){return this.currentRoute||(this.currentRoute=window.location.pathname),!!(this.currentRoute===e||e==="/dashboard"&&(this.currentRoute==="/"||this.currentRoute==="")||e==="/jobs"&&this.currentRoute.startsWith("/job/"))}updateActiveStates(){document.querySelectorAll(".nav-link[data-route]").forEach(t=>{const s=t.getAttribute("data-route");this.isActiveRoute(s)?(t.classList.remove("btn-outline-primary"),t.classList.add("btn-primary")):(t.classList.remove("btn-primary"),t.classList.add("btn-outline-primary"))})}updateStatus(e){const t=document.getElementById("nav-connection-status");if(t){const a=t.querySelector(".status-dot");e.connected?(a.className="status-dot bg-success",a.title=`Connected via ${e.connectionType||"unknown"}`):(a.className="status-dot bg-warning",a.title="Disconnected - using fallback")}const s=document.getElementById("nav-queue-count");if(s&&e.queue){const a=(e.queue.pending||0)+(e.queue.processing||0);s.textContent=a,s.className=a>0?"badge bg-warning":"badge bg-info"}}setupEventHandlers(){document.addEventListener("click",t=>{const s=t.target.closest(".nav-link[data-route]");if(s){t.preventDefault();const a=s.getAttribute("data-route");m.navigate(a)}});const e=document.getElementById("nav-refresh-btn");e&&e.addEventListener("click",()=>{window.dispatchEvent(new CustomEvent("nav-refresh-requested"))})}addNavigationLink(e){this.navigationData.links.push(e)}removeNavigationLink(e){this.navigationData.links=this.navigationData.links.filter(t=>t.path!==e)}getState(){return{currentRoute:this.currentRoute,links:this.navigationData.links}}cleanup(){console.log("🧭 Navigation Component cleaned up")}}window.toggleQueueDashboard=()=>{const l=document.getElementById("queue-dashboard");l&&(l.style.display=l.style.display==="none"?"block":"none")};window.clearAllLogs=()=>{if(confirm("Clear all status messages?")){const l=document.getElementById("status-messages");l&&(l.innerHTML="")}};window.showAppStatus=()=>{alert(`App Status: OK
Connection: Active
Build: Production`)};const v=new A;class L{constructor(){this.isInitialized=!1}init(){this.isInitialized||(this.isInitialized=!0)}render(e){console.log("📊 Dashboard: Activating with existing HTML structure"),u.init(),n.init(),h.isInitialized||h.init(),console.log("📊 Dashboard functionality activated")}activate(){document.title="Dashboard - StreamGank Video Generator",h.refreshStatus(),console.log("📊 Dashboard activated")}deactivate(){console.log("📊 Dashboard deactivated")}getState(){const e=y&&typeof y.getFormData=="function",t=n&&typeof n.getState=="function";return{initialized:this.isInitialized,formData:e?y.getFormData():null,uiState:t?n.getState():null}}cleanup(){this.isInitialized=!1,console.log("📊 Dashboard Page cleaned up")}}const P=new L;class x{constructor(){this.currentJobId=null,this.jobData=null,this.refreshTimer=null,this.refreshInterval=5e3}async render(e,t={}){const{jobId:s}=t;if(!e){console.error("📄 JobDetail: No container provided");return}if(!s){console.error("📄 JobDetail: No job ID provided"),this.renderError(e,"No job ID specified");return}this.currentJobId=s,e.innerHTML=this.createLoadingTemplate();try{await this.loadJobData(s),e.innerHTML=this.createJobTemplate(),this.startAutoRefresh(),console.log(`📄 JobDetail rendered for job: ${s}`)}catch(a){console.error("📄 JobDetail render error:",a),this.renderError(e,a.message)}}async loadJobData(e){try{let t=p.getJob(e);if(!t){const s=await d.getJobStatus(e);s.success&&(t=s.job)}if(!t)throw new Error(`Job ${e} not found`);this.jobData=t,document.title=`Job ${e} - StreamGank`}catch(t){throw new Error(`Failed to load job data: ${t.message}`)}}createLoadingTemplate(){return`
            <div class="job-detail-page">
                <div class="container-fluid">
                    <!-- Header with navigation -->
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Loading Job...</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <!-- Loading State -->
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-3 text-muted">Loading job details...</p>
                    </div>
                </div>
            </div>
        `}createJobTemplate(){var a,o,r,i,c,g;const e=this.jobData,t=this.getStatusClass(e.status),s=this.getStatusIcon(e.status);return`
            <div class="job-detail-page">
                <div class="container-fluid">
                    <!-- Header with navigation and actions -->
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Job ${e.id}</h1>
                            <div class="mt-1">
                                <span class="badge ${t} me-2">${s} ${e.status.toUpperCase()}</span>
                                <small class="text-muted">Created: ${this.formatDate(e.createdAt)}</small>
                            </div>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                            ${this.createActionButtons(e)}
                        </div>
                    </div>

                    <div class="row">
                        <!-- Left Column - Job Information -->
                        <div class="col-md-6">
                            <!-- Job Parameters -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">📋 Job Parameters</h5>
                                </div>
                                <div class="card-body">
                                    <dl class="row mb-0">
                                        <dt class="col-sm-4">Country:</dt>
                                        <dd class="col-sm-8">${((a=e.params)==null?void 0:a.country)||"N/A"}</dd>
                                        
                                        <dt class="col-sm-4">Platform:</dt>
                                        <dd class="col-sm-8">${((o=e.params)==null?void 0:o.platform)||"N/A"}</dd>
                                        
                                        <dt class="col-sm-4">Genre:</dt>
                                        <dd class="col-sm-8">${((r=e.params)==null?void 0:r.genre)||"N/A"}</dd>
                                        
                                        <dt class="col-sm-4">Content Type:</dt>
                                        <dd class="col-sm-8">${((i=e.params)==null?void 0:i.contentType)||"N/A"}</dd>
                                        
                                        <dt class="col-sm-4">Template:</dt>
                                        <dd class="col-sm-8">${((c=e.params)==null?void 0:c.template)||"Default"}</dd>
                                        
                                        ${(g=e.params)!=null&&g.url?`
                                        <dt class="col-sm-4">Source URL:</dt>
                                        <dd class="col-sm-8">
                                            <a href="${e.params.url}" target="_blank" class="text-break">
                                                ${e.params.url}
                                            </a>
                                        </dd>
                                        `:""}
                                    </dl>
                                </div>
                            </div>

                            <!-- Job Timeline -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">⏱️ Timeline</h5>
                                </div>
                                <div class="card-body">
                                    ${this.createTimeline(e)}
                                </div>
                            </div>

                            <!-- Video Result (if available) -->
                            ${e.videoUrl?this.createVideoResult(e):""}
                        </div>

                        <!-- Right Column - Progress and Status -->
                        <div class="col-md-6">
                            <!-- Progress Card -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">📊 Progress</h5>
                                </div>
                                <div class="card-body">
                                    <div class="mb-3">
                                        <div class="d-flex justify-content-between mb-1">
                                            <span class="fw-medium">${e.currentStep||"Processing"}</span>
                                            <span class="text-muted">${e.progress||0}%</span>
                                        </div>
                                        <div class="progress">
                                            <div class="progress-bar ${this.getProgressClass(e.progress)}" 
                                                 role="progressbar" style="width: ${e.progress||0}%">
                                            </div>
                                        </div>
                                    </div>
                                    
                                    ${e.error?`
                                    <div class="alert alert-danger">
                                        <h6 class="alert-heading">❌ Error</h6>
                                        <p class="mb-0">${e.error}</p>
                                    </div>
                                    `:""}
                                    
                                    ${e.creatomateId?`
                                    <div class="mt-3">
                                        <h6>🎬 Creatomate Render</h6>
                                        <p class="mb-1">
                                            <strong>ID:</strong> 
                                            <code>${e.creatomateId}</code>
                                        </p>
                                        <button class="btn btn-outline-primary btn-sm" onclick="checkCreatomateStatus('${e.creatomateId}')">
                                            Check Render Status
                                        </button>
                                    </div>
                                    `:""}
                                </div>
                            </div>

                            <!-- Queue Information -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="mb-0">📋 Queue Information</h5>
                                </div>
                                <div class="card-body">
                                    <dl class="row mb-0">
                                        <dt class="col-sm-6">Queue Position:</dt>
                                        <dd class="col-sm-6">${e.queuePosition||"N/A"}</dd>
                                        
                                        <dt class="col-sm-6">Processing Time:</dt>
                                        <dd class="col-sm-6">${this.calculateDuration(e)}</dd>
                                        
                                        <dt class="col-sm-6">Last Updated:</dt>
                                        <dd class="col-sm-6">${this.formatDate(e.updatedAt||e.createdAt)}</dd>
                                    </dl>
                                </div>
                            </div>

                            <!-- Status Messages -->
                            <div class="card">
                                <div class="card-header">
                                    <h5 class="mb-0">📝 Status Messages</h5>
                                </div>
                                <div class="card-body">
                                    <div id="job-status-messages" class="status-messages" style="max-height: 300px; overflow-y: auto;">
                                        <!-- Status messages will be populated here -->
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `}createActionButtons(e){const t=[];return(e.status==="processing"||e.status==="pending")&&t.push(`
                <button class="btn btn-warning me-2" onclick="cancelJob('${e.id}')">
                    ⏹️ Cancel Job
                </button>
            `),e.status==="failed"&&t.push(`
                <button class="btn btn-primary me-2" onclick="retryJob('${e.id}')">
                    🔄 Retry Job
                </button>
            `),t.push(`
            <button class="btn btn-outline-secondary me-2" onclick="refreshJobData('${e.id}')">
                🔄 Refresh
            </button>
        `),t.join("")}createTimeline(e){const t=[];return t.push({time:e.createdAt,status:"created",message:"Job created and queued"}),e.startedAt&&t.push({time:e.startedAt,status:"started",message:"Job processing started"}),e.completedAt&&t.push({time:e.completedAt,status:"completed",message:"Job completed successfully"}),t.map(s=>`
            <div class="timeline-item mb-3">
                <div class="d-flex align-items-start">
                    <div class="timeline-icon me-3">
                        ${this.getStatusIcon(s.status)}
                    </div>
                    <div class="timeline-content">
                        <p class="mb-1 fw-medium">${s.message}</p>
                        <small class="text-muted">${this.formatDate(s.time)}</small>
                    </div>
                </div>
            </div>
        `).join("")}createVideoResult(e){return`
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">🎬 Video Result</h5>
                </div>
                <div class="card-body">
                    <video controls class="w-100 mb-3" style="max-height: 400px;">
                        <source src="${e.videoUrl}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="d-flex gap-2">
                        <a href="${e.videoUrl}" target="_blank" class="btn btn-primary">
                            🔗 Open Video
                        </a>
                        <a href="${e.videoUrl}" download class="btn btn-outline-secondary">
                            💾 Download
                        </a>
                        <button class="btn btn-outline-info" onclick="copyToClipboard('${e.videoUrl}')">
                            📋 Copy URL
                        </button>
                    </div>
                </div>
            </div>
        `}startAutoRefresh(){this.stopAutoRefresh(),this.jobData&&["pending","processing"].includes(this.jobData.status)&&(this.refreshTimer=setInterval(()=>{this.refreshJobData(this.currentJobId)},this.refreshInterval),console.log(`📄 Auto-refresh started for job ${this.currentJobId}`))}stopAutoRefresh(){this.refreshTimer&&(clearInterval(this.refreshTimer),this.refreshTimer=null)}async refreshJobData(e){try{if(await this.loadJobData(e),this.currentJobId===e){const t=document.querySelector(".job-detail-page").parentElement;await this.render(t,{jobId:e})}}catch(t){console.error("📄 Failed to refresh job data:",t)}}renderError(e,t){e.innerHTML=`
            <div class="job-detail-page">
                <div class="container-fluid">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Job Not Found</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <div class="alert alert-danger">
                        <h4 class="alert-heading">❌ Error</h4>
                        <p class="mb-0">${t}</p>
                        <hr>
                        <a href="/dashboard" class="btn btn-primary">Return to Dashboard</a>
                    </div>
                </div>
            </div>
        `}activate(e){console.log(`📄 JobDetail activated for job: ${e.jobId}`)}deactivate(){this.stopAutoRefresh(),console.log("📄 JobDetail deactivated")}getStatusClass(e){return{pending:"bg-warning",processing:"bg-info",completed:"bg-success",failed:"bg-danger",cancelled:"bg-secondary"}[e]||"bg-secondary"}getStatusIcon(e){return{created:"➕",started:"▶️",pending:"⏳",processing:"🔄",completed:"✅",failed:"❌",cancelled:"⏹️"}[e]||"📄"}getProgressClass(e){return e>=100?"bg-success":e>=75?"bg-info":e>=50?"bg-warning":"bg-primary"}formatDate(e){return e?new Date(e).toLocaleString():"N/A"}calculateDuration(e){if(!e.startedAt)return"Not started";const t=new Date(e.startedAt),a=(e.completedAt?new Date(e.completedAt):new Date)-t;return n.formatDuration(a)}cleanup(){this.stopAutoRefresh(),console.log("📄 JobDetail Page cleaned up")}}window.cancelJob=async l=>{if(confirm("Are you sure you want to cancel this job?"))try{await p.cancelJob(l)&&location.reload()}catch(e){alert(`Failed to cancel job: ${e.message}`)}};window.retryJob=l=>{alert("Retry functionality not yet implemented")};window.refreshJobData=l=>{location.reload()};window.checkCreatomateStatus=async l=>{try{const e=await d.getCreatomateStatus(l);e.success?alert(`Creatomate Status: ${e.status}
Progress: ${e.progress||"N/A"}%`):alert(`Error: ${e.message}`)}catch(e){alert(`Error checking status: ${e.message}`)}};window.copyToClipboard=async l=>{try{await navigator.clipboard.writeText(l),alert("URL copied to clipboard!")}catch{alert("Failed to copy URL")}};const R=new x;class B{constructor(){this.isInitialized=!1,this.currentPage=null,this.appContainer=null,this.modules={dom:u,router:m,api:d,realtime:h,jobs:p,ui:n,form:y,navigation:v},this.pages={dashboard:P,jobDetail:R}}async init(){if(this.isInitialized){console.warn("⚠️ App already initialized");return}try{await this.initializeCore(),this.setupAppContainer(),this.setupRouting(),await this.initializeServices(),await this.initializeComponents(),this.setupEventHandlers(),this.startServices(),this.isInitialized=!0}catch(e){console.error("❌ Failed to initialize app:",e),this.handleInitializationError(e)}}async initializeCore(){u.init()}setupAppContainer(){this.appContainer=document.body,this.mainContent=document.querySelector(".main-content")||document.querySelector(".container-fluid")||this.appContainer}setupRouting(){m.addRoute("/",()=>this.renderPage("dashboard"),{title:"Dashboard - StreamGank Video Generator"}),m.addRoute("/dashboard",()=>this.renderPage("dashboard"),{title:"Dashboard - StreamGank Video Generator"}),m.addRoute("/job/:jobId",e=>this.renderPage("jobDetail",e),{title:"Job Details - StreamGank Video Generator"}),m.addRoute("/jobs",()=>this.renderJobsPage(),{title:"All Jobs - StreamGank Video Generator"}),m.addEventListener("routeChange",e=>{}),m.addEventListener("notFound",e=>{console.warn(`🛤️ Route not found: ${e.detail.path}`),m.navigate("/dashboard",{replace:!0})})}async initializeServices(){p.init()}async initializeComponents(){v.init(),await M.init(),P.init()}setupEventHandlers(){document.addEventListener("formSubmit",e=>{this.handleFormSubmission(e.detail)}),p.addEventListener("jobStarted",e=>{console.log("💼 Job started:",e.detail.job.id)}),p.addEventListener("jobCompleted",e=>{console.log("✅ Job completed:",e.detail.job.id)}),p.addEventListener("jobFailed",e=>{console.error("❌ Job failed:",e.detail.job.id,e.detail.error)}),h.addEventListener("connected",e=>{console.log("📡 Real-time connection established:",e.detail.type),v.updateStatus({connected:!0,connectionType:e.detail.type})}),h.addEventListener("disconnected",e=>{console.warn("📡 Real-time connection lost:",e.detail.type),v.updateStatus({connected:!1,connectionType:e.detail.type})}),h.addEventListener("queueUpdate",e=>{v.updateStatus({connected:!0,queue:e.detail.stats})}),window.addEventListener("nav-refresh-requested",()=>{h.refreshStatus()}),v.setupEventHandlers()}setupButtonHandlers(){const e=u.get("refreshQueueBtn");e&&e.addEventListener("click",()=>{h.refreshStatus()});const t=u.get("clearQueueBtn");t&&t.addEventListener("click",async()=>{if(confirm("Are you sure you want to clear the entire queue? This will cancel all pending jobs."))try{(await d.clearQueue()).success?n.addStatusMessage("success","✅","Queue cleared successfully"):n.addStatusMessage("error","❌","Failed to clear queue")}catch(o){n.addStatusMessage("error","❌",`Error clearing queue: ${o.message}`)}});const s=u.get("checkStatusBtn");s&&s.addEventListener("click",()=>{this.handleManualStatusCheck()});const a=u.get("loadVideoBtn");a&&a.addEventListener("click",()=>{this.handleManualVideoLoad()})}startServices(){m.init(),h.init()}async renderPage(e,t={}){try{if(this.currentPage&&this.pages[this.currentPage]&&typeof this.pages[this.currentPage].deactivate=="function"&&this.pages[this.currentPage].deactivate(),e==="dashboard")n.init(),await y.init(),window.FormManager=y,this.pages[e]&&typeof this.pages[e].activate=="function"&&this.pages[e].activate(t),this.currentPage=e;else if(e==="jobDetail")await this.renderJobDetailPage(t),this.currentPage=e;else throw new Error(`Page '${e}' not found`)}catch(s){console.error(`🎨 Failed to render page '${e}':`,s),alert(`Error: ${s.message}`)}}async renderJobDetailPage(e){const{jobId:t}=e,s=`
            <div class="modal fade" id="jobDetailModal" tabindex="-1" aria-labelledby="jobDetailModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="jobDetailModalLabel">Job ${t}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="jobDetailContent">
                            <div class="text-center py-4">
                                <div class="spinner-border" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-3">Loading job details...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;let a=document.getElementById("jobDetailModal");a||(document.body.insertAdjacentHTML("beforeend",s),a=document.getElementById("jobDetailModal")),new bootstrap.Modal(a).show();try{const r=document.getElementById("jobDetailContent");this.pages.jobDetail&&typeof this.pages.jobDetail.render=="function"&&await this.pages.jobDetail.render(r,e)}catch(r){console.error("Failed to load job details:",r),document.getElementById("jobDetailContent").innerHTML=`
                <div class="alert alert-danger">
                    <h6>Error</h6>
                    <p>Failed to load job details: ${r.message}</p>
                </div>
            `}a.addEventListener("hidden.bs.modal",()=>{m.navigate("/dashboard")})}renderJobsPage(){const e=document.getElementById("app-content");e&&(e.innerHTML=`
            <div class="jobs-page">
                <div class="container-fluid">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h1 class="h3">All Jobs</h1>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <div class="alert alert-info">
                        <h4 class="alert-heading">🚧 Under Construction</h4>
                        <p class="mb-0">
                            The jobs page is coming soon! For now, you can view individual jobs by visiting 
                            <code>/job/[job-id]</code> or return to the 
                            <a href="/dashboard" class="alert-link">Dashboard</a>.
                        </p>
                    </div>
                </div>
            </div>
        `,console.log("🎨 Jobs page rendered (placeholder)"))}renderErrorPage(e,t){e.innerHTML=`
            <div class="error-page">
                <div class="container-fluid">
                    <div class="text-center py-5">
                        <h1 class="h2 text-danger">⚠️ Error</h1>
                        <p class="lead">${t}</p>
                        <div class="mt-4">
                            <a href="/dashboard" class="btn btn-primary">Return to Dashboard</a>
                        </div>
                    </div>
                </div>
            </div>
        `}async handleFormSubmission(e){const{formData:t,previewUrl:s,validation:a}=e;console.log("📋 Form submitted:",t);try{const o={country:t.country,platform:t.platform,genre:t.genre,template:t.template,contentType:t.contentType,url:s};await p.startVideoGeneration(o),console.log("🔄 Refreshing dashboard to show new job..."),window.ProcessTable&&typeof window.ProcessTable.loadRecentJobs=="function"&&setTimeout(()=>{window.ProcessTable.loadRecentJobs()},1e3)}catch(o){console.error("❌ Form submission failed:",o),n.addStatusMessage("error","❌",`Generation failed: ${o.message}`)}}async handleManualStatusCheck(){const e=u.get("creatomateIdDisplay");if(!e||!e.textContent){n.addStatusMessage("warning","⚠️","No Creatomate ID available for status check");return}const t=e.textContent.trim();try{n.addStatusMessage("info","🔍","Checking render status...");const s=await d.getCreatomateStatus(t);if(s.success&&s.videoUrl)n.addStatusMessage("success","🎬","Video is ready!"),n.displayVideo({jobId:`manual-${Date.now()}`,videoUrl:s.videoUrl,creatomateId:t});else if(s.success&&s.status){const a=s.status.charAt(0).toUpperCase()+s.status.slice(1);n.addStatusMessage("info","⏳",`Render status: ${a}`)}else n.addStatusMessage("error","❌",`Status check failed: ${s.message||"Unknown error"}`)}catch(s){console.error("❌ Manual status check failed:",s),n.addStatusMessage("error","❌",`Status check error: ${s.message}`)}}handleManualVideoLoad(){const e=prompt("Enter Creatomate render ID:");if(!e||!e.trim()){n.addStatusMessage("warning","⚠️","No render ID provided");return}const t=e.trim(),s=u.get("creatomateIdDisplay");s&&(s.textContent=t),n.addStatusMessage("info","📥",`Loading video for render ID: ${t}`),this.handleManualStatusCheck()}handleInitializationError(e){const t=`Failed to initialize application: ${e.message}`;try{n.addStatusMessage("error","❌",t,!1)}catch{console.error("❌",t),alert(t)}}getStatus(){return{initialized:this.isInitialized,modules:Object.fromEntries(Object.entries(this.modules).map(([e,t])=>[e,typeof t.getStatus=="function"?t.getStatus():"ready"])),realtime:h.getConnectionStatus(),jobs:p.getJobStats(),api:d.getCacheStats()}}async restart(){console.log("🔄 Restarting application..."),this.cleanup(),this.isInitialized=!1,setTimeout(async()=>{await this.init()},1e3)}stopAllPolling(){console.log("🛑 ANTI-SPAM: Stopping all polling timers..."),window.ProcessTable&&typeof window.ProcessTable.stopPeriodicUpdates=="function"&&window.ProcessTable.stopPeriodicUpdates(),console.log("✅ All polling stopped (anti-spam mode)")}cleanup(){console.log("🧹 Cleaning up application resources..."),this.stopAllPolling(),Object.values(this.modules).forEach(e=>{typeof e.cleanup=="function"&&e.cleanup()}),console.log("✅ Application cleaned up")}}const w=new B;document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>{w.init()}):w.init();window.StreamGankApp=w;
//# sourceMappingURL=main.2EdwWIJO.js.map
