import{A as d,D as g,U as r,R as h}from"./RealtimeService.oh9Ulcj5.js";(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))s(a);new MutationObserver(a=>{for(const o of a)if(o.type==="childList")for(const i of o.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&s(i)}).observe(document,{childList:!0,subtree:!0});function t(a){const o={};return a.integrity&&(o.integrity=a.integrity),a.referrerPolicy&&(o.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?o.credentials="include":a.crossOrigin==="anonymous"?o.credentials="omit":o.credentials="same-origin",o}function s(a){if(a.ep)return;a.ep=!0;const o=t(a);fetch(a.href,o)}})();class M{constructor(){this.routes=new Map,this.currentRoute=null,this.isStarted=!1,console.log("🔧 SimpleRouter created")}addRoute(e,t){console.log(`📝 Adding route: ${e}`);const s=[],a=e.replace(/:([^/]+)/g,(i,n)=>(s.push(n),"([^/]+)")),o=new RegExp(`^${a}$`);this.routes.set(e,{handler:t,regex:o,paramNames:s,originalPath:e}),console.log(`✅ Route added: ${e}`)}navigate(e){console.log(`🚀 Navigate to: ${e}`),window.history.pushState({},"",e),this.handleRoute(e)}handleRoute(e=window.location.pathname){console.log(`🔍 Handling route: ${e}`);for(const[t,s]of this.routes){const a=e.match(s.regex);if(a){console.log(`✅ Route matched: ${t}`);const o={};s.paramNames.forEach((i,n)=>{o[i]=a[n+1]}),console.log("📋 Route params:",o);try{return s.handler(o),this.currentRoute=t,!0}catch(i){console.error("❌ Route handler error:",i)}}}return console.warn(`❌ No route matched for: ${e}`),this.handle404(e),!1}handle404(e){console.log(`🔍 404 for path: ${e}`),e!=="/dashboard"&&e!=="/"&&!e.startsWith("/dashboard")?(console.log(`🏠 Redirecting to dashboard from: ${e}`),this.navigate("/dashboard")):console.warn(`❌ Route not found and cannot redirect: ${e}`)}start(){if(this.isStarted){console.warn("⚠️ Router already started");return}console.log("🎬 Starting router..."),window.addEventListener("popstate",()=>{console.log("🔄 Popstate event"),this.handleRoute()}),this.handleRoute(),this.isStarted=!0,console.log("✅ Router started")}}const m=new M;class k{constructor(){this.genresByCountry={},this.templatesByGenre={},this.platformsByCountry={},this.formState={country:"",platform:"",platforms:[],genre:"",genres:[],template:"",contentType:""},this.isValidating=!1,this.validationCache=new Map,this.isInitialized=!1}async init(){if(this.isInitialized){console.log("📋 FormManager already initialized, skipping...");return}await this.loadFormConfiguration(),this.setupEventListeners(),this.initializeFormState(),this.isInitialized=!0,console.log("✅ FormManager initialized successfully")}async loadFormConfiguration(){this.loadGenresByCountry(),this.loadTemplatesByGenre(),await this.initializePlatformData()}loadGenresByCountry(){this.genresByCountry={FR:{"Action & Aventure":"Action & Adventure",Animation:"Animation",Comédie:"Comedy","Crime & Thriller":"Crime & Thriller",Documentaire:"Documentary",Drame:"Drama",Fantastique:"Fantasy","Film de guerre":"War Movies",Histoire:"History",Horreur:"Horror","Musique & Musicale":"Music & Musical","Mystère & Thriller":"Mystery & Thriller","Pour enfants":"Kids","Reality TV":"Reality TV","Réalisé en Europe":"Made in Europe","Science-Fiction":"Science Fiction","Sport & Fitness":"Sport & Fitness",Western:"Western"},US:{"Action & Adventure":"Action & Adventure",Animation:"Animation",Comedy:"Comedy",Crime:"Crime",Documentary:"Documentary",Drama:"Drama",Fantasy:"Fantasy",History:"History",Horror:"Horror","Kids & Family":"Kids & Family","Made in Europe":"Made in Europe","Music & Musical":"Music & Musical","Mystery & Thriller":"Mystery & Thriller","Reality TV":"Reality TV",Romance:"Romance","Science-Fiction":"Science-Fiction",Sport:"Sport","War & Military":"War & Military",Western:"Western"}}}loadTemplatesByGenre(){this.templates={cc6718c5363e42b282a123f99b94b335:{name:"Default Template",genres:["default"]},ed21a309a5c84b0d873fde68642adea3:{name:"Horror",genres:["Horror"]},"7f8db20ddcd94a33a1235599aa8bf473":{name:"Action Adventure",genres:["Action & Adventure"]},bc62f68a6b074406b571df42bdc6b71a:{name:"Romance",genres:["Romance"]}},this.templatesByGenre={},Object.entries(this.templates).forEach(([e,t])=>{t.genres.forEach(s=>{this.templatesByGenre[s]=e})})}async initializePlatformData(){const e=document.getElementById("country");if(e){const s=e.value||"US";await this.updatePlatformDropdown(s)}const t=e?e.value:"US";await this.updateGenreDropdown(t),this.updateTemplateDropdown(),this.setDefaultSelections(),this.refreshFormState(),this.disableGenerateButton(),console.log("✅ Platform data initialization complete")}async updatePlatformDropdown(e){const t=`platforms_${e}`;if(!this.validationCache.has(t))try{const s=await d.get(`/api/platforms/${e}`);s.success&&s.platforms?(this.populatePlatformSelect(s.platforms),this.validationCache.set(t,!0),console.log("✅ Platform dropdown update completed")):console.error("❌ Invalid platform API response:",s)}catch(s){console.error("❌ Failed to load platforms:",s)}}async updateGenreDropdown(e){const t=`genres_${e}`;if(this.validationCache.has(t)){console.log(`📋 Using cached genres for ${e}`);return}try{console.log(`📋 Loading genres for ${e}...`);const s=await d.get(`/api/genres/${e}`);s.success&&s.genres?(console.log(`📋 API returned ${s.genres.length} genres:`,s.genres),this.populateGenreSelect(s.genres),this.validationCache.set(t,!0),console.log("✅ Genre dropdown update completed")):console.error("❌ Invalid genre API response:",s)}catch(s){console.error("❌ Failed to load genres:",s)}}updateTemplateDropdown(){const e=document.getElementById("template");e&&(e.innerHTML='<option value="">Select Template...</option>',Object.entries(this.templates).forEach(([t,s])=>{const a=document.createElement("option");a.value=t,a.textContent=s.name,e.appendChild(a)}),e.value="cc6718c5363e42b282a123f99b94b335")}setupEventListeners(){if(this.eventListenersSetup)return;const e=document.getElementById("country");e&&e.addEventListener("change",n=>{this.handleCountryChange(n.target.value)});const t=document.getElementById("platform");t&&t.addEventListener("change",n=>{this.handlePlatformChange(n.target.value)});const s=document.getElementById("template");s&&s.addEventListener("change",n=>{this.handleTemplateChange(n.target.value)});const a=document.getElementById("refresh-preview-btn");a&&a.addEventListener("click",()=>{this.loadMoviePreview()});const o=document.querySelectorAll('input[name="contentType"]');o&&Array.from(o).forEach(n=>{n.addEventListener("change",c=>{c.target.checked&&this.handleContentTypeChange(c.target.value)})});const i=document.getElementById("generate-video");i&&i.addEventListener("click",n=>{n.preventDefault(),this.handleFormSubmit()}),this.eventListenersSetup=!0}initializeFormState(){const e=document.getElementById("country");e&&!e.value&&(e.value="US"),this.ensureContentTypeSelected(),console.log("📋 Form state initialization complete")}ensureContentTypeSelected(){const e=document.querySelectorAll('input[name="contentType"]'),t=Array.from(e).find(s=>s.checked);if(console.log("📋 Content Type Radios found:",e.length),console.log("📋 Already checked:",t?t.value:"none"),!t&&e.length>0){const s=Array.from(e).find(a=>a.value==="Serie");s?(s.checked=!0,console.log("📋 Force-selected Serie (TV Shows) radio button")):(e[0].checked=!0,console.log("📋 Force-selected first radio button:",e[0].value))}}refreshFormState(){const e=g.getFormData();Object.assign(this.formState,e),console.log("📋 Form state updated"),console.log("📋 Final form data:",this.formState),this.updatePreviewWithMovies()}setDefaultSelections(){let e=!1;const t=document.getElementById("platform");if(t&&t.children.length>1&&t.selectedIndex===0){let a=-1;for(let o=1;o<t.options.length;o++)if(t.options[o].value.toLowerCase().includes("netflix")){a=o;break}t.selectedIndex=a>0?a:1,this.formState.platform=t.value,console.log("📋 Set default platform:",this.formState.platform),e=!0}const s=document.getElementById("genre");if(s&&s.children.length>1&&s.selectedIndex===0){let a=-1;for(let o=1;o<s.options.length;o++)if(s.options[o].value.toLowerCase().includes("horror")){a=o;break}s.selectedIndex=a>0?a:1,this.formState.genre=s.value,console.log("📋 Set default genre:",this.formState.genre),e=!0,this.updateTemplates(this.formState.genre)}e&&console.log("📋 Defaults set")}manualRefresh(){return console.log("📋 Manual form refresh triggered"),this.refreshFormState(),this.formState}async handleCountryChange(e){console.log(`📋 Country changed: ${e}`),this.formState.country=e,this.resetPlatformSelection(),this.resetGenreSelection(),this.resetTemplateSelection(),e&&await this.updatePlatforms(e),this.updatePreview()}async handlePlatformChange(){const e=[];document.querySelectorAll('input[name="platforms"]:checked').forEach(s=>{e.push(s.value)}),console.log("📺 Platform selection changed:",e),this.formState.platforms=e,this.formState.platform=e[0]||"",this.resetGenreSelection(),this.resetTemplateSelection(),this.updatePreviewWithMovies()}handleGenreChange(){const e=[];document.querySelectorAll('input[name="genres"]:checked').forEach(s=>{e.push(s.value)}),console.log("🎭 Genre selection changed:",e),this.formState.genres=e,this.formState.genre=e[0]||"",this.resetTemplateSelection(),e.length>0&&this.updateTemplates(e[0]),this.updatePreviewWithMovies()}handleTemplateChange(e){console.log(`📋 Template changed: ${e}`),this.formState.template=e,this.updatePreview()}handleContentTypeChange(e){console.log(`📋 Content type changed: ${e}`),this.formState.contentType=e,this.updatePreviewWithMovies()}async updatePlatforms(e){try{const t=await d.getPlatforms(e);t.success&&t.platforms?this.populatePlatformSelect(t.platforms):this.populateDefaultPlatforms(e)}catch(t){console.error("❌ Failed to load platforms:",t),this.populateDefaultPlatforms(e)}}populatePlatformSelect(e){const t=document.getElementById("platform-checkboxes");if(!t){console.error("❌ Platform checkboxes container not found!");return}console.log("📋 Populating platforms:",e),t.innerHTML="",e.forEach((s,a)=>{const o=document.createElement("div");o.className="checkbox-item";const i=document.createElement("input");i.type="checkbox",i.id=`platform-${a}`,i.value=s,i.name="platforms",s.toLowerCase().includes("netflix")&&(i.checked=!0,this.formState.platforms=[s]);const n=document.createElement("label");n.htmlFor=`platform-${a}`,n.textContent=s,i.addEventListener("change",c=>{this.handlePlatformChange()}),o.appendChild(i),o.appendChild(n),t.appendChild(o)}),console.log("✅ Platform checkboxes populated with",e.length,"options")}populateDefaultPlatforms(e){const t=[{value:"Netflix",name:"Netflix"},{value:"Prime Video",name:"Prime Video"},{value:"Disney+",name:"Disney+"},{value:"Apple TV+",name:"Apple TV+"},{value:"HBO Max",name:"HBO Max"}];this.populatePlatformSelect(t)}async updateGenres(e,t=null){const s=`genres_${e}`;if(this.validationCache.has(s)){console.log(`📋 Using cached genres for ${e}`);return}try{console.log(`📋 Loading genres for ${e}...`);const a=await d.getGenres(e);if(a.success&&a.genres){console.log(`📋 API returned ${a.genres.length} genres for ${e}:`,a.genres),this.populateGenreSelect(a.genres),this.validationCache.set(s,!0);return}}catch(a){console.error("❌ Failed to load genres from API:",a)}console.log(`📋 Using fallback static genres for ${e}`),this.populateGenreSelectFromStatic(e)}populateGenreSelect(e){const t=document.getElementById("genre-checkboxes");if(!t){console.error("❌ Genre checkboxes container not found!");return}console.log("📋 Populating genres:",e),t.innerHTML="",e.forEach((s,a)=>{const o=document.createElement("div");o.className="checkbox-item";const i=document.createElement("input");i.type="checkbox",i.id=`genre-${a}`,i.value=s,i.name="genres",s.toLowerCase().includes("horror")&&(i.checked=!0,this.formState.genres=[s]);const n=document.createElement("label");n.htmlFor=`genre-${a}`,n.textContent=s,i.addEventListener("change",c=>{this.handleGenreChange()}),o.appendChild(i),o.appendChild(n),t.appendChild(o)}),console.log("✅ Genre checkboxes populated with",e.length,"options")}populateGenreSelectFromStatic(e){const t=this.genresByCountry[e];if(!t)return;const s=document.getElementById("genre");if(s){for(;s.children.length>1;)s.removeChild(s.lastChild);Object.entries(t).forEach(([a,o])=>{const i=document.createElement("option");i.value=o,i.textContent=a,s.appendChild(i)})}}updateTemplates(e){const t=document.getElementById("template");if(!t)return;const s=this.getTemplateForGenre(e);Array.from(t.options).forEach(a=>{a.value===s&&(a.selected=!0,this.formState.template=s)}),console.log(`📋 Template auto-selected for genre '${e}': ${s}`)}getTemplateForGenre(e){if(this.templatesByGenre[e])return this.templatesByGenre[e];const t=e.toLowerCase();for(const[s,a]of Object.entries(this.templatesByGenre))if(s.toLowerCase()===t)return a;return this.templatesByGenre.default}resetPlatformSelection(){const e=document.getElementById("platform");if(e)for(e.selectedIndex=0;e.children.length>1;)e.removeChild(e.lastChild);this.formState.platform=""}resetGenreSelection(){const e=document.getElementById("genre");if(e)for(e.selectedIndex=0;e.children.length>1;)e.removeChild(e.lastChild);this.formState.genre=""}resetTemplateSelection(){const e=document.getElementById("template");e&&(e.selectedIndex=0),this.formState.template=""}validateForm(){const e=[],t=[];return this.formState.country||e.push("Country is required"),this.formState.platform||e.push("Platform is required"),this.formState.genre||e.push("Genre is required"),this.formState.contentType||e.push("Content type is required"),this.formState.template||t.push("No template selected - default will be used"),{isValid:e.length===0,errors:e,warnings:t}}async validateStreamGankUrl(e){if(!e||e.includes("Select all parameters"))return{valid:!1,message:"Please complete the form to generate a valid URL"};const t=`url:${e}`;if(this.validationCache.has(t))return this.validationCache.get(t);try{r.addStatusMessage("info","🔍","Validating URL..."),this.isValidating=!0;const s=await d.validateUrl(e),a={valid:s.success,message:s.message,moviesCount:s.moviesCount,timestamp:new Date().toISOString()};return this.validationCache.set(t,a),a.valid?r.addStatusMessage("success","✅",`URL validated! Found ${a.moviesCount} items`):r.addStatusMessage("error","❌",`URL validation failed: ${a.message}`),a}catch(s){console.error("❌ URL validation error:",s);const a={valid:!1,message:s.message||"Validation failed",timestamp:new Date().toISOString()};return r.addStatusMessage("error","❌",`Validation error: ${a.message}`),a}finally{this.isValidating=!1}}async handleFormSubmit(){try{this.updateFormStateFromDOM();const e=this.validateForm();if(!e.isValid){e.errors.forEach(a=>{r.addStatusMessage("error","❌",a)});return}e.warnings.forEach(a=>{r.addStatusMessage("warning","⚠️",a)});const t=this.generateStreamGankUrl(),s=await this.validateStreamGankUrl(t);if(!s.valid)return;document.dispatchEvent(new CustomEvent("formSubmit",{detail:{formData:{...this.formState},previewUrl:t,validation:s}}))}catch(e){console.error("❌ Form submission error:",e),r.addStatusMessage("error","❌",`Form submission failed: ${e.message}`)}}updateFormStateFromDOM(){const e=g.getFormData();Object.assign(this.formState,e)}updatePreview(){r.updateFormPreviewFromState(this.formState),console.log("📋 Preview updated")}updatePreviewWithMovies(){this.updatePreview(),this.loadMoviePreview(),console.log("📋 Preview updated with movie reload")}async loadMoviePreview(){const e=this.formState.country,t=this.formState.platforms||[],s=this.formState.genres||[],a=this.formState.contentType;if(!e||t.length===0||s.length===0){this.hideMoviePreview();return}console.log("🎬 Loading movie preview:",{country:e,platforms:t,genres:s,contentType:a}),this.showMoviePreviewLoading();try{const i=await(await fetch("/api/movies/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({country:e,platforms:t,genre:s,contentType:a==="All"?null:a})})).json();i.success&&i.movies&&i.movies.length>0?this.displayMoviePreview(i.movies):this.showMoviePreviewEmpty()}catch(o){console.error("❌ Failed to load movie preview:",o),this.showMoviePreviewEmpty()}}displayMoviePreview(e){const t=document.getElementById("movie-preview-container"),s=document.getElementById("movie-preview-grid"),a=document.getElementById("movie-preview-loading"),o=document.getElementById("movie-preview-empty");!t||!s||(a.style.display="none",o.style.display="none",s.innerHTML="",e.forEach((i,n)=>{const c=this.createMovieCard(i,n);s.appendChild(c)}),t.style.display="block",this.enableGenerateButton(),console.log(`✅ Displayed ${e.length} movie preview cards`))}createMovieCard(e,t){var p;const s=document.createElement("div");s.className="card bg-dark border-secondary h-100 shadow-sm",s.style.width="200px",s.style.minWidth="200px",s.style.cursor="pointer";const a=e.poster_url||e.backdrop_url||"https://via.placeholder.com/300x450/1a1a1a/16c784?text=No+Image",o=e.title||"Unknown Title",i=e.year||"Unknown Year",n=e.imdb||e.rating||"No Rating",c=(p=n.toString().match(/(\d+\.?\d*)/))==null?void 0:p[1],u=c?`⭐ ${c}/10`:n;return s.innerHTML=`
            <img src="${a}" alt="${o}" class="card-img-top" 
                 style="height: 250px; object-fit: cover;"
                 onerror="this.src='https://via.placeholder.com/300x450/1a1a1a/16c784?text=No+Image'"
                 loading="lazy">
            <div class="card-body p-2">
                <h6 class="card-title text-light mb-1" style="font-size: 0.9rem; line-height: 1.2;">${o}</h6>
                <p class="card-text mb-1">
                    <small class="text-success fw-bold">${i}</small>
                </p>
                <p class="card-text">
                    <small class="text-warning">${u}</small>
                </p>
            </div>
        `,s.addEventListener("mouseenter",()=>{s.classList.add("shadow-lg"),s.style.transform="translateY(-5px)",s.style.transition="all 0.3s ease"}),s.addEventListener("mouseleave",()=>{s.classList.remove("shadow-lg"),s.style.transform="translateY(0)"}),s.addEventListener("click",()=>{console.log(`🎬 Movie selected: ${o} (${i})`)}),s}showMoviePreviewLoading(){const e=document.getElementById("movie-preview-container"),t=document.getElementById("movie-preview-loading"),s=document.getElementById("movie-preview-grid"),a=document.getElementById("movie-preview-empty");!e||!t||(e.style.display="block",t.style.display="block",s.innerHTML="",a.style.display="none",this.disableGenerateButton())}showMoviePreviewEmpty(){const e=document.getElementById("movie-preview-container"),t=document.getElementById("movie-preview-loading"),s=document.getElementById("movie-preview-grid"),a=document.getElementById("movie-preview-empty");!e||!a||(e.style.display="block",t.style.display="none",s.innerHTML="",a.style.display="block",this.disableGenerateButton())}hideMoviePreview(){const e=document.getElementById("movie-preview-container");e&&(e.style.display="none"),this.disableGenerateButton()}enableGenerateButton(){const e=document.getElementById("generate-video");e&&(e.disabled=!1,e.classList.remove("btn-secondary"),e.classList.add("btn-primary"),e.innerHTML='<span class="icon">🎬</span> Generate Video',console.log("✅ Generate button enabled"))}disableGenerateButton(){const e=document.getElementById("generate-video");e&&(e.disabled=!0,e.classList.remove("btn-primary"),e.classList.add("btn-secondary"),e.innerHTML='<span class="icon">⚠️</span> No Movies Available',console.log("🚫 Generate button disabled"))}generateStreamGankUrl(){if(!this.formState.country||!this.formState.platform||!this.formState.contentType)return"Select all parameters to generate URL";const e="https://streamgank.com",t=new URLSearchParams;if(this.formState.country&&t.set("country",this.formState.country),this.formState.platform&&t.set("platforms",this.formState.platform.toLowerCase()),this.formState.genre&&this.formState.genre!=="all"){const a={Horreur:"Horror","Action & Aventure":"Action",Animation:"Animation"}[this.formState.genre]||this.formState.genre;t.set("genres",a)}if(this.formState.contentType&&this.formState.contentType!=="all"){const a={movies:"Film",series:"Serie",tvshows:"Serie","tv-shows":"Serie"}[this.formState.contentType.toLowerCase()]||this.formState.contentType;t.set("type",a)}return`${e}?${t.toString()}`}getFormData(){return this.updateFormStateFromDOM(),{...this.formState}}setFormData(e){Object.assign(this.formState,e),Object.entries(e).forEach(([t,s])=>{const a=g.get(`${t}Select`)||g.get(t);a&&a.value!==void 0&&(a.value=s)}),this.updatePreview()}resetForm(){this.formState={country:"",platform:"",genre:"",template:"",contentType:""},["country","platform","genre","template"].forEach(t=>{const s=document.getElementById(t);s&&(s.selectedIndex=0)});const e=g.get("contentTypeRadios");e&&Array.from(e).forEach(t=>{t.checked=!1}),this.validationCache.clear(),this.updatePreview(),console.log("📋 Form reset")}getValidationState(){return{isValidating:this.isValidating,cacheSize:this.validationCache.size,lastValidation:null}}emit(e,t){console.log(`📤 FormManager emitting ${e}:`,t);const s=new CustomEvent(e,{detail:t});document.dispatchEvent(s)}}const y=new k;class ${constructor(){this.isInitialized=!1}init(){this.isInitialized||(this.isInitialized=!0)}render(e){console.log("📊 Dashboard: Activating with existing HTML structure"),g.init(),r.init(),h.isInitialized||h.init(),console.log("📊 Dashboard functionality activated")}activate(){document.title="Dashboard - StreamGank Video Generator",h.refreshStatus(),console.log("📊 Dashboard activated")}deactivate(){console.log("📊 Dashboard deactivated")}getState(){const e=y&&typeof y.getFormData=="function",t=r&&typeof r.getState=="function";return{initialized:this.isInitialized,formData:e?y.getFormData():null,uiState:t?r.getState():null}}cleanup(){this.isInitialized=!1,console.log("📊 Dashboard Page cleaned up")}}class J extends EventTarget{constructor(){super(),this.activeJobs=new Map,this.jobHistory=new Map,this.currentJob=null,this.maxJobHistory=100,this.monitoringInterval=5e3,this.monitoringTimer=null,this.isGenerationActive=!1,this.creatomateMessages=new Set}init(){this.setupEventListeners()}setupEventListeners(){window.addEventListener("beforeunload",()=>{this.cleanup()})}async startVideoGeneration(e){try{if(this.validateGenerationParams(e),this.isGenerationActive)throw new Error("Another video generation is already in progress");this.isGenerationActive=!0,r.showProgress(),r.disableGenerateButton("Starting generation..."),r.addStatusMessage("info","🚀","Starting video generation..."),this.creatomateMessages.clear();const t=await d.generateVideo(e);if(!t.success)throw new Error(t.message||"Failed to start video generation");const s=this.createJobObject(t,e);return this.activeJobs.set(s.id,s),this.currentJob=s,this.startJobMonitoring(s.id),r.addStatusMessage("success","✅",`Job queued successfully! ${s.queuePosition?`Position: ${s.queuePosition}`:""}`),r.updateProgress(5,"Job queued, waiting to start..."),this.dispatchEvent(new CustomEvent("jobStarted",{detail:{job:s}})),console.log(`💼 Job started: ${s.id}`),{success:!0,job:s}}catch(t){throw console.error("❌ Failed to start video generation:",t),this.resetGenerationState(),r.addStatusMessage("error","❌",`Failed to start generation: ${t.message}`),this.dispatchEvent(new CustomEvent("jobError",{detail:{error:t}})),t}}createJobObject(e,t){return{id:e.jobId,params:t,status:"pending",progress:0,createdAt:new Date().toISOString(),startedAt:null,completedAt:null,queuePosition:e.queuePosition||0,error:null,result:null,creatomateId:null,videoUrl:null}}validateGenerationParams(e){const s=["country","platform","genre","contentType"].filter(a=>!e[a]);if(s.length>0)throw new Error(`Missing required parameters: ${s.join(", ")}`);console.log("✅ Parameters validated:",e)}async startJobMonitoring(e){this.monitoringTimer&&clearInterval(this.monitoringTimer),console.log(`👀 Started monitoring job: ${e}`),this.monitoringTimer=setInterval(async()=>{try{await this.updateJobStatus(e)}catch(t){console.error("❌ Job monitoring error:",t),this.consecutiveErrors>3&&(this.stopJobMonitoring(),r.addStatusMessage("warning","⚠️","Job monitoring stopped due to repeated errors"))}},this.monitoringInterval)}stopJobMonitoring(){this.monitoringTimer&&(clearInterval(this.monitoringTimer),this.monitoringTimer=null,console.log("⏹️ Job monitoring stopped"))}async updateJobStatus(e){if(this.activeJobs.get(e))try{const s=await d.getJobStatus(e);s.success&&s.job&&this.processJobUpdate(s.job)}catch(s){throw console.error(`❌ Failed to update job status for ${e}:`,s),s}}processJobUpdate(e){const t=this.activeJobs.get(e.id);if(!t)return;const s=t.status,a=t.progress;Object.assign(t,{status:e.status,progress:e.progress||0,currentStep:e.currentStep,startedAt:e.startedAt||t.startedAt,completedAt:e.completedAt,error:e.error,result:e,creatomateId:e.creatomateId,videoUrl:e.videoUrl}),s!==t.status&&this.handleJobStatusChange(t,s),a!==t.progress&&this.updateJobProgress(t),t.creatomateId&&!t.videoUrl&&t.status==="completed"&&this.startCreatomateMonitoring(t),this.dispatchEvent(new CustomEvent("jobUpdated",{detail:{job:t,previousStatus:s}})),console.log(`💼 Job ${t.id} updated: ${t.status} (${t.progress}%)`)}handleJobStatusChange(e,t){switch(e.status){case"processing":t==="pending"&&(r.addStatusMessage("info","⚡","Job started processing!"),e.startedAt=new Date().toISOString());break;case"completed":this.handleJobCompletion(e);break;case"failed":this.handleJobFailure(e);break;case"cancelled":this.handleJobCancellation(e);break}}handleJobCompletion(e){console.log(`✅ Job completed: ${e.id}`),e.videoUrl?this.finishSuccessfulGeneration(e):e.creatomateId?(r.updateProgress(90,"Python script completed, video rendering..."),r.addStatusMessage("info","🎬",`Video rendering started (ID: ${e.creatomateId}). Monitoring progress...`),this.startCreatomateMonitoring(e)):(r.addStatusMessage("warning","⚠️","Job completed but video URL not yet available"),this.moveJobToHistory(e)),this.dispatchEvent(new CustomEvent("jobCompleted",{detail:{job:e}}))}startCreatomateMonitoring(e){let t=0;const s=40,a=async()=>{t++;try{const o=await d.getCreatomateStatus(e.creatomateId);if(o.success&&o.videoUrl)e.videoUrl=o.videoUrl,e.result.videoUrl=o.videoUrl,this.finishSuccessfulGeneration(e);else if(o.success&&o.status){const i=o.status.toLowerCase(),n=i.charAt(0).toUpperCase()+i.slice(1);if(t%4===0){const u=`rendering-update-${Math.floor(t/4)}`;this.creatomateMessages.has(u)||(r.addStatusMessage("info","⏳",`Video status: ${n}... (${t}/${s})`),this.creatomateMessages.add(u))}let c=90+t/s*10;(i.includes("render")||i.includes("process"))&&(c=Math.min(95,c)),r.updateProgress(c,`Rendering: ${n}`),t<s?setTimeout(()=>a(),3e4):this.handleCreatomateTimeout(e)}else this.handleCreatomateError(e,o.message,t,s,a)}catch(o){this.handleCreatomateNetworkError(e,o,t,s,a)}};a()}handleCreatomateTimeout(e){const t="creatomate-timeout";this.creatomateMessages.has(t)||(r.addStatusMessage("warning","⚠️",'Video rendering is taking longer than expected. Use "Check Status" to monitor manually.'),this.creatomateMessages.add(t)),r.enableGenerateButton(),this.isGenerationActive=!1}handleCreatomateError(e,t,s,a,o){const i=`creatomate-error-${t}`;this.creatomateMessages.has(i)||(r.addStatusMessage("error","❌",`Render status check failed: ${t||"Unknown error"}`),this.creatomateMessages.add(i)),s<a?setTimeout(()=>o(),3e4):(r.addStatusMessage("error","❌","Unable to check render status after multiple attempts."),this.moveJobToHistory(e))}handleCreatomateNetworkError(e,t,s,a,o){console.error("Creatomate status check error:",t);const i=`network-error-${s}`;s%3===0&&!this.creatomateMessages.has(i)&&(r.addStatusMessage("warning","⚠️",`Network error checking render status (attempt ${s})`),this.creatomateMessages.add(i)),s<a?setTimeout(()=>o(),3e4):(r.addStatusMessage("error","❌","Network errors prevented render status monitoring."),this.moveJobToHistory(e))}finishSuccessfulGeneration(e){r.updateProgress(100,"Generation completed!"),r.addStatusMessage("success","🎉","Video generation completed successfully!"),r.displayVideo({jobId:e.id,videoUrl:e.videoUrl,creatomateId:e.creatomateId,timestamp:new Date().toLocaleString()}),this.moveJobToHistory(e),this.resetGenerationState()}handleJobFailure(e){console.error(`❌ Job failed: ${e.id}`,e.error),r.updateProgress(0,"Generation failed"),r.addStatusMessage("error","❌",`Generation failed: ${e.error||"Unknown error"}`,!1),this.moveJobToHistory(e),this.dispatchEvent(new CustomEvent("jobFailed",{detail:{job:e}})),this.resetGenerationState()}handleJobCancellation(e){console.log(`⏹️ Job cancelled: ${e.id}`),r.addStatusMessage("warning","⏹️","Job was cancelled"),this.moveJobToHistory(e),this.dispatchEvent(new CustomEvent("jobCancelled",{detail:{job:e}})),this.resetGenerationState()}updateJobProgress(e){e===this.currentJob&&r.updateProgress(e.progress,e.currentStep||"Processing...")}resetGenerationState(){r.hideProgress(),r.enableGenerateButton(),this.isGenerationActive=!1,this.stopJobMonitoring()}async cancelJob(e){try{const t=await d.cancelJob(e);if(t.success)return r.addStatusMessage("info","⏹️","Job cancellation requested"),!0;throw new Error(t.message||"Failed to cancel job")}catch(t){return console.error("❌ Failed to cancel job:",t),r.addStatusMessage("error","❌",`Failed to cancel job: ${t.message}`),!1}}stopVideoGeneration(){this.currentJob&&this.cancelJob(this.currentJob.id),this.resetGenerationState(),r.addStatusMessage("warning","⏹️","Video generation stopped")}moveJobToHistory(e){this.activeJobs.delete(e.id),this.jobHistory.set(e.id,{...e,movedToHistoryAt:new Date().toISOString()}),this.currentJob&&this.currentJob.id===e.id&&(this.currentJob=null),this.limitJobHistory()}limitJobHistory(){if(this.jobHistory.size>this.maxJobHistory){const e=Array.from(this.jobHistory.entries()),t=e.slice(0,e.length-this.maxJobHistory);t.forEach(([s])=>{this.jobHistory.delete(s)}),console.log(`🧹 Cleaned up ${t.length} old job records`)}}getJob(e){return this.activeJobs.get(e)||this.jobHistory.get(e)||null}getActiveJobs(){return Array.from(this.activeJobs.values())}getJobStats(){var e;return{active:this.activeJobs.size,history:this.jobHistory.size,total:this.activeJobs.size+this.jobHistory.size,currentJob:((e=this.currentJob)==null?void 0:e.id)||null,isMonitoring:!!this.monitoringTimer,isGenerationActive:this.isGenerationActive}}cleanup(){this.stopJobMonitoring(),console.log("🧹 Job Manager cleaned up")}}const C=new J;class I{constructor(){this.currentJobId=null,this.jobData=null,this.refreshTimer=null,this.refreshInterval=5e3}async render(e,t={}){console.log("📄 JobDetail.render() called with:",{container:!!e,params:t});const{jobId:s}=t;if(console.log("📄 JobDetail extracted jobId:",s),!e){console.error("📄 JobDetail: No container provided");return}if(!s){console.error("📄 JobDetail: No job ID provided"),console.error("📄 JobDetail: Full params received:",JSON.stringify(t,null,2)),this.renderError(e,"No job ID specified");return}this.currentJobId=s,e.innerHTML=this.createLoadingTemplate();try{await this.loadJobData(s),e.innerHTML=this.createJobTemplate(),this.startAutoRefresh(),console.log(`📄 JobDetail rendered for job: ${s}`)}catch(a){console.error("📄 JobDetail render error:",a),this.renderError(e,a.message)}}async loadJobData(e){try{let t=C.getJob(e);if(!t){const s=await d.getJobStatus(e);s.success&&(t=s.job)}if(!t)throw new Error(`Job ${e} not found`);this.jobData=t,document.title=`Job ${e} - StreamGank`}catch(t){throw new Error(`Failed to load job data: ${t.message}`)}}createLoadingTemplate(){return`
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
                        <p class="mt-3 text-light">Loading job details...</p>
                    </div>
                </div>
            </div>
        `}createJobTemplate(){var a,o,i,n,c,u,p,v,f,b;const e=this.jobData,t=this.getStatusClass(e.status),s=this.getStatusIcon(e.status);return`
            <style>
              /* Fix container overflow */
              .main-content {
                overflow-x: hidden !important;
              }
              
              /* Compact Timeline Styles */
              .timeline-compact {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 0.75rem;
                padding: 0;
              }
              .timeline-step {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid #495057;
                border-radius: 8px;
                padding: 0.75rem;
                text-align: center;
                position: relative;
                transition: all 0.3s ease;
              }
              .timeline-step.completed {
                border-color: #198754;
                background: rgba(25, 135, 84, 0.1);
              }
              .timeline-step.active {
                border-color: #0d6efd;
                background: rgba(13, 110, 253, 0.1);
                animation: pulse 2s infinite;
              }
              .timeline-step.pending {
                border-color: #6c757d;
                background: rgba(108, 117, 125, 0.1);
              }
              .timeline-step.failed {
                border-color: #dc3545;
                background: rgba(220, 53, 69, 0.1);
              }

              .step-icon {
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
              }
              .step-title {
                font-size: 0.8rem;
                font-weight: 600;
                margin: 0;
                color: #fff;
              }
              .step-status {
                font-size: 0.7rem;
                margin-top: 0.25rem;
                opacity: 0.8;
              }

              /* Compact Cards */
              .compact-card {
                margin-bottom: 1rem;
              }
              .compact-card .card-header {
                padding: 0.5rem 1rem;
                font-size: 0.9rem;
              }
              .compact-card .card-body {
                padding: 1rem;
              }

              /* Override for video result section - extra compact */
              #creatomate-section .card-header {
                padding: 0.5rem 0.75rem !important;
              }
              #creatomate-section .card-body {
                padding: 0.5rem 0.75rem !important;
              }

              /* Progress Bar Compact */
              .progress-compact {
                height: 12px;
                border-radius: 6px;
                background: #343a40;
              }

              /* Parameter Inline Display - NO CARDS */
              .param-inline {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                align-items: center;
              }
              .param-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.3rem;
                padding: 0.25rem 0.4rem;
                border-radius: 4px;
                background: rgba(13, 110, 253, 0.1);
                border: 1px solid rgba(13, 110, 253, 0.3);
                font-size: 0.75rem;
                max-width: 100%;
                overflow: hidden;
              }
              .param-badge i {
                font-size: 0.7rem;
                color: #0d6efd;
              }
              .param-badge .label {
                color: #e6edf3;
                margin-right: 0.25rem;
              }
              .param-badge .value {
                color: #fff;
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 120px;
              }

              /* Stats Compact */
              .stats-row {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 0.4rem;
              }
              .stat-item {
                text-align: center;
                padding: 0.4rem 0.2rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                min-width: 0;
                overflow: hidden;
              }
              .stat-value {
                font-size: 1rem;
                font-weight: bold;
                margin-bottom: 0.25rem;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
              }
              .stat-label {
                font-size: 0.65rem;
                color: #e6edf3;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
              }

              /* Video player fixes */
              #result-video {
                width: 100%;
                height: auto;
                display: block !important;
                background: #000;
                object-fit: contain;
              }

              #result-video::-webkit-media-controls-panel {
                background-color: rgba(0, 0, 0, 0.8);
              }

              /* Video container spacing */
              .video-container {
                max-width: 600px;
                width: 100%;
                position: relative;
                background: #1a1a1a;
                border-radius: 8px;
                overflow: hidden;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
              }

              /* Compact video container for inline display */
              .video-container-compact {
                width: 100%;
                position: relative;
                background: #1a1a1a;
                border-radius: 6px;
                overflow: hidden;
                min-height: 160px;
                display: flex;
                align-items: center;
                justify-content: center;
              }

              /* Collapsible sections */
              .section-toggle {
                cursor: pointer;
                user-select: none;
              }
              .section-toggle:hover {
                background: rgba(255, 255, 255, 0.1);
              }

              @keyframes pulse {
                0%,
                100% {
                  transform: scale(1);
                }
                50% {
                  transform: scale(1.05);
                }
              }

              /* Responsive adjustments */
              @media (max-width: 768px) {
                .timeline-compact {
                  grid-template-columns: repeat(2, 1fr);
                  gap: 0.5rem;
                }
                .param-inline {
                  gap: 0.4rem;
                }
                .stats-row {
                  grid-template-columns: repeat(2, 1fr);
                  gap: 0.3rem;
                }
                .param-badge {
                  font-size: 0.7rem;
                  padding: 0.2rem 0.3rem;
                }
                .stat-value {
                  font-size: 0.9rem;
                }
                .stat-label {
                  font-size: 0.6rem;
                }
              }
              
              @media (max-width: 576px) {
                .timeline-compact {
                  grid-template-columns: 1fr;
                }
                .stats-row {
                  grid-template-columns: repeat(2, 1fr);
                }
                .container-fluid {
                  padding-left: 0.5rem !important;
                  padding-right: 0.5rem !important;
                }
              }
            </style>

            <div id="job-detail-app" class="w-100" style="background-color: #0d1117; overflow-x: hidden;">
              <!-- Main Content -->
              <div id="main-content" style="overflow-x: hidden;">
                <!-- Compact Header -->
                <nav class="navbar navbar-dark bg-dark border-bottom border-secondary py-2">
                  <div class="container-fluid">
                    <div class="d-flex align-items-center">
                      <button onclick="history.back()" class="btn btn-outline-light btn-sm me-2">
                        <i class="fas fa-arrow-left"></i>
                      </button>
                      <span class="navbar-brand mb-0 h6">
                        <i class="fas fa-tasks me-1"></i>
                        Job
                        <span id="job-id">${e.id}</span>
                      </span>
                      <span class="badge ${t} ms-2 fs-6">${s} ${e.status.toUpperCase()}</span>
                    </div>
                    <div class="d-flex gap-1">
                      <button onclick="location.reload()" class="btn btn-outline-primary btn-sm">
                        <i class="fas fa-sync-alt"></i>
                      </button>
                      <a href="/dashboard" class="btn btn-primary btn-sm">
                        <i class="fas fa-tachometer-alt"></i>
                      </a>
                    </div>
                  </div>
                </nav>

                <div class="container-fluid py-2" style="overflow-x: hidden;">
                  <!-- Progress & Stats Row -->
                  <div class="row g-2 mb-3">
                    <!-- Progress Section -->
                    <div class="col-md-8">
                      <div class="card bg-dark compact-card">
                        <div class="card-header">
                          <i class="fas fa-chart-line me-1"></i>
                          Progress
                          <span class="float-end">${e.progress||0}%</span>
                        </div>
                        <div class="card-body">
                          <div class="progress progress-compact mb-2">
                            <div
                              class="progress-bar ${this.getProgressClass(e.progress)} progress-bar-striped progress-bar-animated"
                              style="width: ${e.progress||0}%"
                            ></div>
                          </div>
                          <small class="text-light">${e.currentStep||"Initializing..."}</small>
                        </div>
                      </div>
                    </div>

                    <!-- Quick Stats -->
                    <div class="col-md-4">
                      <div class="card bg-dark compact-card">
                        <div class="card-header">
                          <i class="fas fa-info-circle me-1"></i>
                          Stats
                        </div>
                        <div class="card-body">
                          <div class="stats-row">
                            <div class="stat-item">
                              <div class="stat-value text-primary">${this.calculateDuration(e)}</div>
                              <div class="stat-label">Duration</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-value text-info">7/7</div>
                              <div class="stat-label">Steps</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-value text-warning">ynlv</div>
                              <div class="stat-label">Worker</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-value text-success">Normal</div>
                              <div class="stat-label">Priority</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Parameters -->
                  <div class="card bg-dark compact-card">
                    <div class="card-header section-toggle" data-bs-toggle="collapse" data-bs-target="#params-section">
                      <i class="fas fa-cog me-1"></i>
                      Job Parameters
                      <i class="fas fa-chevron-down float-end"></i>
                    </div>
                    <div id="params-section" class="collapse show">
                      <div class="card-body">
                        <div class="param-inline">
                          <div class="param-badge">
                            <i class="fas fa-globe"></i>
                            <span class="label">Country:</span>
                            <span class="value">${((a=e.parameters)==null?void 0:a.country)||((o=e.params)==null?void 0:o.country)||"N/A"}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-tv"></i>
                            <span class="label">Platform:</span>
                            <span class="value">${((i=e.parameters)==null?void 0:i.platform)||((n=e.params)==null?void 0:n.platform)||"N/A"}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-film"></i>
                            <span class="label">Genre:</span>
                            <span class="value">${((c=e.parameters)==null?void 0:c.genre)||((u=e.params)==null?void 0:u.genre)||"N/A"}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-tag"></i>
                            <span class="label">Content Type:</span>
                            <span class="value">${((p=e.parameters)==null?void 0:p.contentType)||((v=e.params)==null?void 0:v.contentType)||"N/A"}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-palette"></i>
                            <span class="label">Template:</span>
                            <span class="value">${((f=e.parameters)==null?void 0:f.template)||((b=e.params)==null?void 0:b.template)||"Default"}</span>
                          </div>
                          ${e.workerId?`
                          <div class="param-badge">
                            <i class="fas fa-user"></i>
                            <span class="label">Worker ID:</span>
                            <span class="value">${e.workerId}</span>
                          </div>
                          `:""}
                          ${e.creatomateId?`
                          <div class="param-badge">
                            <i class="fas fa-video"></i>
                            <span class="label">Creatomate ID:</span>
                            <span class="value">${e.creatomateId}</span>
                          </div>
                          `:""}
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Process Timeline -->
                  <div class="card bg-dark compact-card">
                    <div class="card-header section-toggle" data-bs-toggle="collapse" data-bs-target="#timeline-section">
                      <i class="fas fa-list-check me-1"></i>
                      Process Timeline
                      <i class="fas fa-chevron-down float-end"></i>
                    </div>
                    <div id="timeline-section" class="collapse show">
                      <div class="card-body">
                        <div class="timeline-compact">
                          <div class="timeline-step completed">
                            <div class="step-icon">📊</div>
                            <div class="step-title">Database Extraction</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">📝</div>
                            <div class="step-title">Script Generation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">🎨</div>
                            <div class="step-title">Asset Preparation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">🎬</div>
                            <div class="step-title">HeyGen Video Creation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">⏳</div>
                            <div class="step-title">HeyGen Processing</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">📱</div>
                            <div class="step-title">Scroll Video Generation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">🎞️</div>
                            <div class="step-title">Creatomate Assembly</div>
                            <div class="step-status">Ready</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Compact Video Result Section -->
                  ${e.videoUrl||e.creatomateId?`
                  <div class="card bg-dark compact-card">
                    <div class="card-header py-2">
                      <div class="d-flex align-items-center justify-content-between">
                        <div class="d-flex align-items-center">
                          <i class="fas fa-film me-2 text-primary"></i>
                          <span class="fw-bold">Video Result</span>
                          <span class="badge bg-success ms-2">Ready</span>
                        </div>
                        <div class="d-flex gap-1">
                          <button class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-sync-alt me-1"></i>
                            Refresh Status
                          </button>
                        </div>
                      </div>
                    </div>
                    <div class="card-body py-2">
                      ${e.creatomateId?`
                      <!-- Compact Creatomate Info -->
                      <div class="mb-2">
                        <div class="d-flex align-items-center text-sm">
                          <span class="text-light me-2">ID:</span>
                          <code class="text-info small">${e.creatomateId}</code>
                        </div>
                      </div>
                      `:""}

                      ${e.videoUrl?`
                      <!-- Compact Video Player -->
                      <div class="row g-2">
                        <div class="col-md-7">
                          <div class="video-container-compact">
                            <video
                              controls
                              preload="metadata"
                              muted
                              playsinline
                              class="w-100"
                              style="max-height: 580px; border-radius: 6px; position: relative; z-index: 2"
                            >
                              <source src="${e.videoUrl}" type="video/mp4" />
                              Your browser does not support the video tag.
                            </video>
                          </div>
                        </div>
                        <div class="col-md-5">
                          <div class="d-grid gap-1">
                            <a href="${e.videoUrl}" download class="btn btn-sm btn-success">
                              <i class="fas fa-download me-1"></i>
                              Download
                            </a>
                            <button onclick="navigator.clipboard.writeText('${e.videoUrl}')" class="btn btn-sm btn-outline-info">
                              <i class="fas fa-copy me-1"></i>
                              Copy URL
                            </button>
                            <button onclick="document.querySelector('video').requestFullscreen()" class="btn btn-sm btn-outline-secondary">
                              <i class="fas fa-expand me-1"></i>
                              Fullscreen
                            </button>
                          </div>
                        </div>
                      </div>
                      `:""}
                    </div>
                  </div>
                  `:""}

                  <!-- Error Information -->
                  ${e.error?`
                  <div class="card bg-dark border-danger compact-card">
                    <div class="card-header bg-danger">
                      <i class="fas fa-exclamation-triangle me-1"></i>
                      Error Details
                    </div>
                    <div class="card-body">
                      <div class="text-light" style="font-size: 0.8rem">
                        ${e.error}
                      </div>
                    </div>
                  </div>
                  `:""}
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
                        <small class="text-light">${this.formatDate(s.time)}</small>
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
        `}activate(e){console.log(`📄 JobDetail activated for job: ${e.jobId}`)}deactivate(){this.stopAutoRefresh(),console.log("📄 JobDetail deactivated")}getStatusClass(e){return{pending:"bg-warning",processing:"bg-info",completed:"bg-success",failed:"bg-danger",cancelled:"bg-secondary"}[e]||"bg-secondary"}getStatusIcon(e){return{created:"➕",started:"▶️",pending:"⏳",processing:"🔄",completed:"✅",failed:"❌",cancelled:"⏹️"}[e]||"📄"}getProgressClass(e){return e>=100?"bg-success":e>=75?"bg-info":e>=50?"bg-warning":"bg-primary"}formatDate(e){return e?new Date(e).toLocaleString():"N/A"}calculateDuration(e){if(!e.startedAt)return"Not started";const t=new Date(e.startedAt),a=(e.completedAt?new Date(e.completedAt):new Date)-t;return r.formatDuration(a)}cleanup(){this.stopAutoRefresh(),console.log("📄 JobDetail Page cleaned up")}}window.cancelJob=async l=>{if(confirm("Are you sure you want to cancel this job?"))try{await C.cancelJob(l)&&location.reload()}catch(e){alert(`Failed to cancel job: ${e.message}`)}};window.retryJob=l=>{alert("Retry functionality not yet implemented")};window.refreshJobData=l=>{location.reload()};window.checkCreatomateStatus=async l=>{try{const e=await d.getCreatomateStatus(l);e.success?alert(`Creatomate Status: ${e.status}
Progress: ${e.progress||"N/A"}%`):alert(`Error: ${e.message}`)}catch(e){alert(`Error checking status: ${e.message}`)}};window.copyToClipboard=async l=>{try{await navigator.clipboard.writeText(l),alert("URL copied to clipboard!")}catch{alert("Failed to copy URL")}};class E{constructor(){this.jobs=[],this.queueStats={},this.refreshTimer=null,this.refreshInterval=5e3,this.currentFilter="all",this.isInitialized=!1,window.Router=m}async render(e){if(!e){console.error("📋 QueuePage: No container provided");return}e.innerHTML=this.createLoadingTemplate();try{await this.loadQueueData(),e.innerHTML=this.createQueueTemplate(),this.setupEventListeners(),this.startRealTimeUpdates(),console.log("📋 Queue Page rendered successfully"),this.isInitialized=!0}catch(t){console.error("📋 Queue Page render error:",t),this.renderError(e,t.message)}}createLoadingTemplate(){return`
            <div class="queue-page">
                <div class="container-fluid">
                    <!-- Header -->
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <h1 class="h3 mb-0">
                                <i class="fas fa-tasks me-2"></i>
                                Queue Management
                            </h1>
                            <p class="text-light mb-0">Monitor and manage video generation jobs</p>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2 nav-link" data-route="/dashboard">
                                <i class="fas fa-home me-1"></i>Dashboard
                            </a>
                        </div>
                    </div>
                    
                    <!-- Loading State -->
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="text-light">Loading queue data...</p>
                    </div>
                </div>
            </div>
        `}createQueueTemplate(){return`
            <div class="queue-page">
                <div class="container-fluid">
                    <!-- Header with Stats -->
                    <div class="row mb-4">
                        <div class="col-md-8">
                            <h1 class="h3 mb-0">
                                <i class="fas fa-tasks me-2"></i>
                                Queue Management
                            </h1>
                            <p class="text-light mb-0">Monitor and manage video generation jobs</p>
                        </div>
                        <div class="col-md-4 text-end">
                            <a href="/dashboard" class="btn btn-outline-primary me-2 nav-link" data-route="/dashboard">
                                <i class="fas fa-home me-1"></i>Dashboard
                            </a>
                            <button id="refresh-queue" class="btn btn-primary">
                                <i class="fas fa-sync-alt me-1"></i>Refresh
                            </button>
                        </div>
                    </div>

                    <!-- Queue Statistics Cards -->
                    <div class="row mb-4">
                        <div class="col-md-3">
                            <div class="card bg-dark border-warning">
                                <div class="card-body text-center">
                                    <div class="display-6 text-warning" id="stat-pending">0</div>
                                    <div class="text-light">⏳ Pending Jobs</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-dark border-info">
                                <div class="card-body text-center">
                                    <div class="display-6 text-info" id="stat-processing">0</div>
                                    <div class="text-light">🔄 Processing</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-dark border-success">
                                <div class="card-body text-center">
                                    <div class="display-6 text-success" id="stat-completed">0</div>
                                    <div class="text-light">✅ Completed</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-dark border-danger">
                                <div class="card-body text-center">
                                    <div class="display-6 text-danger" id="stat-failed">0</div>
                                    <div class="text-light">❌ Failed</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Worker Pool Status -->
                    <div class="row mb-4">
                        <div class="col-12">
                            <div class="card bg-dark">
                                <div class="card-header">
                                    <h5 class="mb-0">
                                        <i class="fas fa-users me-2"></i>Worker Pool Status
                                    </h5>
                                </div>
                                <div class="card-body">
                                    <div class="row text-center">
                                        <div class="col-md-4">
                                            <div class="border-end">
                                                <div class="h4 text-primary" id="workers-active">0</div>
                                                <div class="text-light">🏃 Active Workers</div>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="border-end">
                                                <div class="h4 text-success" id="workers-available">3</div>
                                                <div class="text-light">💤 Available</div>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="h4 text-info" id="workers-concurrent">Yes</div>
                                            <div class="text-light">⚙️ Concurrent Mode</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Job Controls and Filters -->
                    <div class="row mb-4">
                        <div class="col-md-8">
                            <div class="btn-group me-3" role="group">
                                <button type="button" class="btn btn-outline-secondary filter-btn active" data-filter="all">
                                    All Jobs <span id="count-all" class="badge bg-primary">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-warning filter-btn" data-filter="pending">
                                    Pending <span id="count-pending" class="badge bg-warning">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-info filter-btn" data-filter="processing">
                                    Processing <span id="count-processing" class="badge bg-info">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-success filter-btn" data-filter="completed">
                                    Completed <span id="count-completed" class="badge bg-success">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-danger filter-btn" data-filter="failed">
                                    Failed <span id="count-failed" class="badge bg-danger">0</span>
                                </button>
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            <button id="pause-queue" class="btn btn-outline-warning me-2">
                                <i class="fas fa-pause me-1"></i>Pause Queue
                            </button>
                            <button id="clear-queue" class="btn btn-outline-danger">
                                <i class="fas fa-trash me-1"></i>Clear Failed
                            </button>
                        </div>
                    </div>

                    <!-- Jobs List -->
                    <div class="card bg-dark">
                        <div class="card-header">
                            <h5 class="mb-0">
                                <i class="fas fa-list me-2"></i>Job Queue 
                                <span id="total-jobs-count" class="badge bg-primary ms-2">0</span>
                            </h5>
                        </div>
                        <div class="card-body p-0">
                            <div id="jobs-container" class="jobs-list">
                                <!-- Jobs will be populated here -->
                            </div>
                            
                            <!-- Empty State -->
                            <div id="empty-queue" class="text-center py-5 d-none">
                                <i class="fas fa-inbox fa-3x text-light mb-3"></i>
                                <h5 class="text-light">No jobs in queue</h5>
                                <p class="text-light">Generate a video to see jobs appear here</p>
                                <a href="/dashboard" class="btn btn-primary nav-link" data-route="/dashboard">
                                    <i class="fas fa-plus me-1"></i>Generate Video
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>
                .jobs-list {
                    max-height: 600px;
                    overflow-y: auto;
                }
                
                .job-item {
                    border-bottom: 1px solid #495057;
                    padding: 1rem;
                    transition: background-color 0.2s;
                }
                
                .job-item:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                }
                
                .job-item:last-child {
                    border-bottom: none;
                }
                
                .status-badge {
                    font-size: 0.8rem;
                    padding: 0.25rem 0.5rem;
                }
                
                .filter-btn.active {
                    background-color: #0d6efd;
                    border-color: #0d6efd;
                    color: white;
                }
            </style>
        `}async loadQueueData(){try{console.log("📋 Loading queue data...");try{const e=await d.get("/api/queue/status");e.success&&(this.queueStats=e.stats)}catch(e){console.warn("📋 Failed to load queue stats, using defaults:",e.message),this.queueStats={pending:0,processing:0,completed:0,failed:0,activeWorkers:0,availableWorkers:3,concurrentProcessing:!0}}try{const e=await d.get("/api/queue/jobs");e.success&&(this.jobs=e.jobs||[])}catch(e){console.warn("📋 Failed to load jobs, using empty array:",e.message),this.jobs=[]}console.log(`📋 Loaded ${this.jobs.length} jobs and queue stats`)}catch(e){if(console.error("📋 Failed to load queue data:",e),!this.queueStats)throw e}}updateUI(){this.updateStats(),this.updateJobsList(),console.log("📋 UI updated with latest queue data")}updateStats(){const e=this.queueStats,t=document.getElementById("stat-pending"),s=document.getElementById("stat-processing"),a=document.getElementById("stat-completed"),o=document.getElementById("stat-failed");t&&(t.textContent=e.pending||0),s&&(s.textContent=e.processing||0),a&&(a.textContent=e.completed||0),o&&(o.textContent=e.failed||0);const i=document.getElementById("workers-active"),n=document.getElementById("workers-available"),c=document.getElementById("workers-concurrent");i&&(i.textContent=e.activeWorkers||0),n&&(n.textContent=e.availableWorkers||0),c&&(c.textContent=e.concurrentProcessing?"Yes":"No");const u=this.getJobCounts(),p=document.getElementById("count-all"),v=document.getElementById("count-pending"),f=document.getElementById("count-processing"),b=document.getElementById("count-completed"),S=document.getElementById("count-failed");p&&(p.textContent=u.all),v&&(v.textContent=u.pending),f&&(f.textContent=u.processing),b&&(b.textContent=u.completed),S&&(S.textContent=u.failed);const x=document.getElementById("total-jobs-count");x&&(x.textContent=u.all)}updateJobsList(){const e=document.getElementById("jobs-container"),t=document.getElementById("empty-queue");if(!e)return;const s=this.filterJobs(this.jobs,this.currentFilter);if(s.length===0){e.innerHTML="",t==null||t.classList.remove("d-none");return}t==null||t.classList.add("d-none"),s.sort((a,o)=>a.status==="processing"&&o.status!=="processing"?-1:o.status==="processing"&&a.status!=="processing"?1:new Date(o.createdAt)-new Date(a.createdAt)),e.innerHTML=s.map(a=>this.createJobItem(a)).join("")}createJobItem(e){var i,n,c;const t=this.getStatusClass(e.status),s=this.getStatusIcon(e.status),a=this.calculateDuration(e),o=e.progress||0;return`
            <div class="job-item" data-job-id="${e.id}">
                <div class="row align-items-center">
                    <div class="col-md-1">
                        <span class="badge ${t} status-badge">
                            ${s} ${e.status.toUpperCase()}
                        </span>
                    </div>
                    <div class="col-md-2">
                        <div class="text-light fw-medium">${e.id.slice(-8)}</div>
                        <small class="text-light">${this.formatDate(e.createdAt)}</small>
                    </div>
                    <div class="col-md-3">
                        <div class="text-light">${((i=e.parameters)==null?void 0:i.genre)||"N/A"} • ${((n=e.parameters)==null?void 0:n.platform)||"N/A"}</div>
                        <small class="text-light">${((c=e.parameters)==null?void 0:c.country)||"N/A"}</small>
                    </div>
                    <div class="col-md-2">
                        <div class="progress mb-1" style="height: 6px;">
                            <div class="progress-bar ${this.getProgressClass(o)}" 
                                 style="width: ${o}%"></div>
                        </div>
                        <small class="text-light">${o}% • ${a}</small>
                    </div>
                    <div class="col-md-2">
                        <div class="text-light">${e.currentStep||"Queued"}</div>
                        ${e.error?`<small class="text-danger">${e.error.slice(0,50)}...</small>`:""}
                    </div>
                    <div class="col-md-2 text-end">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="viewJob('${e.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${e.status==="failed"?`
                            <button class="btn btn-sm btn-outline-warning" onclick="retryJob('${e.id}')">
                                <i class="fas fa-redo"></i>
                            </button>
                        `:""}
                        ${["pending","processing"].includes(e.status)?`
                            <button class="btn btn-sm btn-outline-danger" onclick="cancelJob('${e.id}')">
                                <i class="fas fa-stop"></i>
                            </button>
                        `:""}
                    </div>
                </div>
            </div>
        `}setupEventListeners(){var e,t,s;document.querySelectorAll(".filter-btn").forEach(a=>{a.addEventListener("click",o=>{const i=o.currentTarget.dataset.filter;this.setFilter(i)})}),(e=document.getElementById("refresh-queue"))==null||e.addEventListener("click",()=>{this.refreshQueue()}),(t=document.getElementById("pause-queue"))==null||t.addEventListener("click",()=>{this.toggleQueue()}),(s=document.getElementById("clear-queue"))==null||s.addEventListener("click",()=>{this.clearFailedJobs()}),h.addEventListener("queueUpdate",a=>{this.handleQueueUpdate(a.detail)})}setFilter(e){var t;this.currentFilter=e,document.querySelectorAll(".filter-btn").forEach(s=>{s.classList.remove("active")}),(t=document.querySelector(`[data-filter="${e}"]`))==null||t.classList.add("active"),this.updateJobsList()}filterJobs(e,t){return t==="all"?e:e.filter(s=>s.status===t)}getJobCounts(){const e={all:this.jobs.length,pending:0,processing:0,completed:0,failed:0};return this.jobs.forEach(t=>{e[t.status]!==void 0&&e[t.status]++}),e}startRealTimeUpdates(){this.refreshTimer=setInterval(()=>{this.refreshQueue()},this.refreshInterval),h.isInitialized||h.init(),console.log("📋 Real-time updates started")}stopRealTimeUpdates(){this.refreshTimer&&(clearInterval(this.refreshTimer),this.refreshTimer=null),console.log("📋 Real-time updates stopped")}async refreshQueue(){try{await this.loadQueueData(),this.updateUI()}catch(e){console.error("📋 Failed to refresh queue:",e)}}handleQueueUpdate(e){console.log("📋 Received queue update:",e),this.refreshQueue()}async toggleQueue(){const e=document.getElementById("pause-queue"),t=e==null?void 0:e.innerHTML;try{e&&(e.innerHTML='<i class="fas fa-spinner fa-spin me-1"></i>Processing...',e.disabled=!0);const s=await d.post("/api/queue/toggle");if(s.success){const a=s.isProcessing?"resumed":"paused";if(r.addStatusMessage("success","⏸️",`Queue processing ${a}`),e){const o=s.isProcessing?'<i class="fas fa-pause me-1"></i>Pause Queue':'<i class="fas fa-play me-1"></i>Resume Queue';e.innerHTML=o}this.refreshQueue()}}catch(s){console.error("📋 Failed to toggle queue:",s),r.addStatusMessage("error","❌","Failed to toggle queue")}finally{e&&(t&&(e.innerHTML=t),e.disabled=!1)}}async clearFailedJobs(){if(confirm("Clear all failed jobs? This cannot be undone."))try{(await d.post("/api/queue/clear-failed")).success&&(r.addStatusMessage("success","🗑️","Failed jobs cleared"),this.refreshQueue())}catch(e){console.error("📋 Failed to clear failed jobs:",e),r.addStatusMessage("error","❌","Failed to clear jobs")}}renderError(e,t){e.innerHTML=`
            <div class="queue-page">
                <div class="container-fluid">
                    <div class="alert alert-danger">
                        <h4 class="alert-heading">❌ Error</h4>
                        <p class="mb-0">${t}</p>
                        <hr>
                        <button onclick="location.reload()" class="btn btn-primary">Retry</button>
                    </div>
                </div>
            </div>
        `}activate(){document.title="Queue Management - StreamGank",console.log("📋 Queue Page activated")}deactivate(){this.stopRealTimeUpdates(),console.log("📋 Queue Page deactivated")}cleanup(){this.stopRealTimeUpdates(),this.isInitialized=!1,console.log("📋 Queue Page cleaned up")}getStatusClass(e){return{pending:"bg-warning text-dark",processing:"bg-info text-dark",completed:"bg-success",failed:"bg-danger",cancelled:"bg-secondary"}[e]||"bg-secondary"}getStatusIcon(e){return{pending:"⏳",processing:"🔄",completed:"✅",failed:"❌",cancelled:"⏹️"}[e]||"📄"}getProgressClass(e){return e>=100?"bg-success":e>=75?"bg-info":e>=50?"bg-warning":"bg-primary"}formatDate(e){return e?new Date(e).toLocaleString():"N/A"}calculateDuration(e){if(!e.startedAt)return"Not started";const t=new Date(e.startedAt),a=(e.completedAt?new Date(e.completedAt):new Date)-t,o=Math.floor(a/6e4),i=Math.floor(a%6e4/1e3);return o>0?`${o}m ${i}s`:`${i}s`}}window.viewJob=l=>{if(!l||l==="undefined"){console.error("❌ Invalid jobId:",l),r.addStatusMessage("error","❌","Invalid job ID");return}console.log("🔍 Viewing job:",l);try{m.navigate(`/job/${l}`),console.log(`✅ Navigating to job detail page: ${l}`)}catch(e){console.error("❌ Navigation failed:",e),r.addStatusMessage("error","❌","Failed to navigate to job details")}};window.retryJob=async l=>{if(confirm("Retry this job?"))try{(await d.post(`/api/job/${l}/retry`)).success&&(r.addStatusMessage("success","🔄","Job retry initiated"),location.reload())}catch{r.addStatusMessage("error","❌","Failed to retry job")}};window.cancelJob=async l=>{if(confirm("Cancel this job?"))try{(await d.post(`/api/job/${l}/cancel`)).success&&(r.addStatusMessage("success","⏹️","Job cancelled"),location.reload())}catch{r.addStatusMessage("error","❌","Failed to cancel job")}};new E;class P{constructor(){this.currentPage=null,console.log("🔧 StreamGankApp created")}async init(){console.log("🚀 Initializing StreamGank App...");try{this.setupRoutes(),m.start(),console.log("✅ App initialized successfully")}catch(e){console.error("❌ App initialization failed:",e)}}setupRoutes(){console.log("🛤️ Setting up routes..."),m.addRoute("/job/:jobId",e=>{console.log("🎯 Job route matched:",e),this.renderJobDetail(e.jobId)}),m.addRoute("/queue",()=>{console.log("🎯 Queue route"),this.renderQueue()}),m.addRoute("/dashboard",()=>{console.log("🎯 Dashboard route"),this.renderDashboard()}),m.addRoute("/",()=>{console.log("🎯 Root route"),this.renderDashboard()}),console.log("✅ Routes setup complete")}getMainContainer(){return document.querySelector(".main-content")||document.body}renderDashboard(){console.log("🎨 Rendering Dashboard");const e=new $;e.render(),e.activate(),this.updateNavigation("/dashboard"),this.currentPage="dashboard"}async renderQueue(){console.log("🎨 Rendering Queue");const e=this.getMainContainer(),t=new E;await t.render(e),t.activate(),this.updateNavigation("/queue"),this.currentPage="queue"}async renderJobDetail(e){if(console.log("🎨 Rendering Job Detail:",e),!e){console.error("❌ No jobId provided"),m.navigate("/dashboard");return}const t=this.getMainContainer(),s=new I;await s.render(t,{jobId:e}),s.activate({jobId:e}),this.updateNavigation(`/job/${e}`),this.currentPage="jobDetail"}updateNavigation(e){if(document.querySelectorAll(".nav-link").forEach(s=>{s.classList.remove("active")}),e.startsWith("/job/"))return;const t=document.querySelector(`[data-route="${e}"]`);t&&t.classList.add("active")}}console.log("🚀 Main.js loaded");const w=new P;document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>{w.init()}):w.init();window.StreamGankApp=w;window.Router=m;
//# sourceMappingURL=main.BmsiDx3J.js.map
