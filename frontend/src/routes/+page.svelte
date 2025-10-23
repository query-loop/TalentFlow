<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, slide } from 'svelte/transition';

  let loaded = false;
  let backendStatus = 'Checking...';

  onMount(() => {
    loaded = true;
    checkBackendStatus();
    setInterval(checkBackendStatus, 30000); // Check every 30 seconds
  });

  async function checkBackendStatus() {
    try {
      const response = await fetch('/api/health');
      if (response.ok) {
        backendStatus = 'Online';
      } else {
        backendStatus = 'Offline';
      }
    } catch (error) {
      backendStatus = 'Offline';
    }
  }
</script>

<svelte:head>
  <title>TalentFlow - Streamline Your Hiring Process</title>
  <meta name="description" content="Discover TalentFlow, the ultimate tool for efficient and effective talent acquisition.">
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <!-- Hero Section -->
  <section class="bg-white py-20 px-4">
    <div class="max-w-5xl mx-auto text-center" transition:fade={{ duration: 1000 }}>
      {#if loaded}
        <div class="mb-8">
          <span class="inline-block px-4 py-2 bg-gray-100 text-black rounded-full text-sm font-medium mb-4">
            Revolutionizing Recruitment
          </span>
        </div>
        <h1 class="text-4xl md:text-6xl font-bold text-gray-900 mb-6 leading-tight">
          Revolutionize Your Hiring
        </h1>
        <p class="text-lg md:text-xl text-gray-600 mb-10 max-w-3xl mx-auto leading-relaxed">
          TalentFlow empowers you to find, evaluate, and onboard top talent faster than ever. Simplify your recruitment process with cutting-edge AI and intuitive tools designed for modern HR teams.
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <button class="bg-black hover:bg-gray-800 text-white font-semibold py-4 px-10 rounded-lg text-lg transition-all duration-300 shadow-lg hover:shadow-xl">
            Get Started Today
          </button>
          <button class="border-2 border-black text-black hover:bg-black hover:text-white font-semibold py-4 px-10 rounded-lg text-lg transition-all duration-300">
            Learn More
          </button>
        </div>
      {/if}
    </div>
  </section>

  <!-- Features Section -->
  <section class="py-20 px-4 bg-white">
    <div class="max-w-7xl mx-auto">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Why Choose TalentFlow?</h2>
        <p class="text-lg text-gray-600 max-w-2xl mx-auto">Discover the features that make hiring effortless and effective.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="bg-white p-8 rounded-lg shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-300" transition:slide={{ duration: 800, delay: 200 }}>
          <div class="w-16 h-16 bg-black rounded-lg flex items-center justify-center mb-6">
            <span class="text-white text-2xl">🤖</span>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 mb-4">AI-Powered Matching</h3>
          <p class="text-gray-600 leading-relaxed">Leverage advanced AI to match candidates with the perfect roles based on skills, experience, and culture fit.</p>
        </div>
        <div class="bg-white p-8 rounded-lg shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-300" transition:slide={{ duration: 800, delay: 400 }}>
          <div class="w-16 h-16 bg-black rounded-lg flex items-center justify-center mb-6">
            <span class="text-white text-2xl">⚡</span>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 mb-4">Streamlined Workflows</h3>
          <p class="text-gray-600 leading-relaxed">Automate repetitive tasks and streamline your hiring process from application to onboarding.</p>
        </div>
        <div class="bg-white p-8 rounded-lg shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-300" transition:slide={{ duration: 800, delay: 600 }}>
          <div class="w-16 h-16 bg-black rounded-lg flex items-center justify-center mb-6">
            <span class="text-white text-2xl">📊</span>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 mb-4">Data-Driven Insights</h3>
          <p class="text-gray-600 leading-relaxed">Gain valuable insights into your hiring metrics and make informed decisions with comprehensive analytics.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- About Section -->
  <section class="py-20 px-4 bg-gray-50">
    <div class="max-w-5xl mx-auto">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div transition:slide={{ duration: 800, delay: 200 }}>
          <h2 class="text-3xl md:text-4xl font-bold text-gray-900 mb-6">About TalentFlow</h2>
          <p class="text-lg text-gray-700 leading-relaxed mb-6">
            TalentFlow is designed for modern HR teams and recruiters who want to transform their hiring process. Our platform combines the power of AI with user-friendly interfaces to help you attract, assess, and hire top talent efficiently.
          </p>
          <div class="flex items-center space-x-4">
            <div class="flex -space-x-2">
              <div class="w-10 h-10 bg-black rounded-full border-2 border-white"></div>
              <div class="w-10 h-10 bg-gray-400 rounded-full border-2 border-white"></div>
              <div class="w-10 h-10 bg-gray-500 rounded-full border-2 border-white"></div>
            </div>
            <span class="text-gray-600">Trusted by 10,000+ companies</span>
          </div>
        </div>
        <div class="relative" transition:slide={{ duration: 800, delay: 400 }}>
          <div class="bg-white p-8 rounded-lg shadow-lg border border-gray-200">
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-gray-50 p-4 rounded-lg text-center">
                <div class="text-2xl font-bold text-black">50%</div>
                <div class="text-sm text-gray-600">Faster Hiring</div>
              </div>
              <div class="bg-gray-50 p-4 rounded-lg text-center">
                <div class="text-2xl font-bold text-black">90%</div>
                <div class="text-sm text-gray-600">Better Matches</div>
              </div>
              <div class="bg-gray-50 p-4 rounded-lg text-center">
                <div class="text-2xl font-bold text-black">24/7</div>
                <div class="text-sm text-gray-600">AI Support</div>
              </div>
              <div class="bg-gray-50 p-4 rounded-lg text-center">
                <div class="text-2xl font-bold text-black">100%</div>
                <div class="text-sm text-gray-600">Secure</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Contact Section -->
  <section class="py-20 px-4 bg-white">
    <div class="max-w-4xl mx-auto text-center">
      <h2 class="text-3xl md:text-4xl font-bold text-gray-900 mb-6">Ready to Get Started?</h2>
      <p class="text-lg text-gray-700 mb-10">Join thousands of companies transforming their hiring process with TalentFlow.</p>
      <div class="flex flex-col sm:flex-row gap-4 justify-center items-center">
        <button class="bg-black hover:bg-gray-800 text-white font-semibold py-4 px-10 rounded-lg text-lg transition-all duration-300 shadow-lg hover:shadow-xl">
          Start Free Trial
        </button>
        <button class="border-2 border-black text-black hover:bg-black hover:text-white font-semibold py-4 px-10 rounded-lg text-lg transition-all duration-300">
          Schedule Demo
        </button>
      </div>
    </div>
  </section>

  <!-- Footer Navbar -->
  <footer class="bg-gray-900 text-white py-12 px-4">
    <div class="max-w-7xl mx-auto">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
        <div>
          <h3 class="text-2xl font-bold mb-4">TalentFlow</h3>
          <p class="text-gray-400 leading-relaxed">Streamline your hiring process with AI-powered tools and insights.</p>
        </div>
        <div>
          <h4 class="font-semibold mb-4">Product</h4>
          <ul class="space-y-2 text-gray-400">
            <li><a href="#" class="hover:text-white transition-colors">Features</a></li>
            <li><a href="#" class="hover:text-white transition-colors">Pricing</a></li>
            <li><a href="#" class="hover:text-white transition-colors">Integrations</a></li>
          </ul>
        </div>
        <div>
          <h4 class="font-semibold mb-4">Company</h4>
          <ul class="space-y-2 text-gray-400">
            <li><a href="#" class="hover:text-white transition-colors">About</a></li>
            <li><a href="#" class="hover:text-white transition-colors">Blog</a></li>
            <li><a href="#" class="hover:text-white transition-colors">Careers</a></li>
          </ul>
        </div>
        <div>
          <h4 class="font-semibold mb-4">Support</h4>
          <ul class="space-y-2 text-gray-400">
            <li><a href="#" class="hover:text-white transition-colors">Help Center</a></li>
            <li><a href="#" class="hover:text-white transition-colors">Contact</a></li>
            <li><a href="#" class="hover:text-white transition-colors">Privacy</a></li>
          </ul>
        </div>
      </div>
      <div class="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center text-gray-400">
        <p>&copy; {new Date().getFullYear()} TalentFlow. All rights reserved.</p>
        <p class="mt-2 md:mt-0">Backend Status: <span class="font-medium {backendStatus === 'Online' ? 'text-black' : 'text-white'}">{backendStatus}</span></p>
      </div>
      <!-- Status Bar -->
      <div class="mt-4 py-2 px-4 text-center font-medium {backendStatus === 'Online' ? 'bg-black text-white' : 'bg-white text-black'}">
        Backend {backendStatus}
      </div>
    </div>
  </footer>
</div>

<style>
  /* Professional typography */
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  /* Subtle animations */
  h1, h2, h3 {
    animation: fadeInUp 1s ease-out;
  }

  p, button, div {
    animation: fadeInUp 1s ease-out 0.2s both;
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
