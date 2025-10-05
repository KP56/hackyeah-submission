import React, { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import EmailConfig from './components/EmailConfig';
import BackendStatus from './components/BackendStatus';
import Sidebar from './components/Sidebar';
import SmartAutomation from './components/SmartAutomation';
import AutomationChat from './components/AutomationChat';
import YourActions from './components/YourActions';
import AppUsage from './components/AppUsage';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backendConnected, setBackendConnected] = useState(false);
  const [shownSuggestions, setShownSuggestions] = useState(new Set());
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    // Set initial state to show connecting screen
    setLoading(true);
    setBackendConnected(false);

    // Try to load config immediately
    loadConfig();

    // Listen for backend status updates from Electron
    const handleBackendStatus = (event, data) => {
      console.log('Backend status update:', data);
      if (data.status === 'starting') {
        setLoading(true);
        setBackendConnected(false);
      }
    };

    const handleBackendError = (event, data) => {
      console.error('Backend error:', data);
      setBackendConnected(false);
      setLoading(true); // Keep loading screen on error
    };
    
    // Listen for switch to automation tab (from desktop popup)
    const handleSwitchToAutomation = () => {
      console.log('Switching to automation chat');
      setActiveTab('chat');
    };
    

    // Add event listeners for Electron IPC
    if (window.electronAPI) {
      window.electronAPI.onBackendStatus(handleBackendStatus);
      window.electronAPI.onBackendError(handleBackendError);
      
      // Listen for switch-to-automation message
      if (window.electronAPI.onSwitchToAutomation) {
        window.electronAPI.onSwitchToAutomation(handleSwitchToAutomation);
      }
      

      return () => {
        window.electronAPI.removeBackendStatusListener(handleBackendStatus);
        window.electronAPI.removeBackendErrorListener(handleBackendError);
      };
    }
  }, []);

  // Handle window resize for responsive behavior
  useEffect(() => {
    const handleResize = () => {
      const newWidth = window.innerWidth;
      setWindowWidth(newWidth);
      
      // Auto-collapse sidebar on small screens
      if (newWidth < 768) {
        setSidebarCollapsed(true);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const loadConfig = async () => {
    try {
      console.log('App: Loading config...');
      console.log('App: electronAPI available?', !!window.electronAPI);
      const configData = await window.electronAPI.getConfig();
      console.log('App: Received config:', configData);
      setConfig(configData);
      setBackendConnected(true);
      setLoading(false); // Only hide loading screen on success
    } catch (error) {
      console.error('Failed to load config:', error);
      setBackendConnected(false);
      setLoading(true); // Keep loading screen on any error
    }
  };

  // Check backend connection periodically
  useEffect(() => {
    if (!backendConnected) {
      // Start with frequent checks, then slow down
      let attemptCount = 0;
      const checkConnection = () => {
        attemptCount++;
        loadConfig();

        // Increase interval after first few attempts
        const interval = attemptCount <= 5 ? 1000 : 3000; // 1s for first 5 attempts, then 3s
        setTimeout(checkConnection, interval);
      };

      // Start checking after 500ms
      const timer = setTimeout(checkConnection, 500);
      return () => clearTimeout(timer);
    }
  }, [backendConnected]);

  // Poll for pending automation suggestions and show desktop popup
  useEffect(() => {
    if (!backendConnected) return;

    const pollSuggestions = async () => {
      try {
        const data = await window.electronAPI.getPendingSuggestions();
        if (data.suggestions && data.suggestions.length > 0) {
          // Check if user is already working on a suggestion (in chat)
          const activeSuggestion = data.suggestions.find(
            s => s.status === 'accepted' || s.status === 'explained'
          );
          
          // Don't show new popups if user is working on one
          if (activeSuggestion) {
            console.log('User is busy with a suggestion, not showing new popups');
            return;
          }
          
          // Show desktop popup only for NEW pending suggestions we haven't shown yet
          for (const suggestion of data.suggestions) {
            if (suggestion.status === 'pending' && !shownSuggestions.has(suggestion.suggestion_id)) {
              console.log('Showing new suggestion popup:', suggestion.suggestion_id);
              await window.electronAPI.showAutomationPopup(suggestion);
              setShownSuggestions(prev => new Set([...prev, suggestion.suggestion_id]));
              break; // Show one at a time
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
      }
    };

    // Poll every 2 seconds (fast response)
    const interval = setInterval(pollSuggestions, 2000);
    
    // Also check immediately
    pollSuggestions();

    return () => clearInterval(interval);
  }, [backendConnected, shownSuggestions]);

  const updateConfig = async (newConfig) => {
    try {
      console.log('App: Updating config...', newConfig);

      // Transform nested config to flat format expected by backend
      const flatConfig = {
        nylas_api_key: newConfig.nylas?.api_key,
        nylas_client_id: newConfig.nylas?.client_id,
        nylas_redirect_uri: newConfig.nylas?.redirect_uri,
        nylas_api_uri: newConfig.nylas?.api_uri,
        gemini_api_key: newConfig.gemini?.api_key,
        gemini_model: newConfig.gemini?.model,
        watch_dirs: newConfig.watch?.dirs,
        pattern_agent_interval_seconds: newConfig.watch?.pattern_interval_seconds,
        recent_ops_capacity: newConfig.watch?.recent_ops_capacity,
        logging_enabled: newConfig.logging?.enabled,
        backend_port: newConfig.backend?.port
      };

      const response = await window.electronAPI.updateConfig(flatConfig);
      console.log('App: Config updated successfully', response);
      setConfig(newConfig);
      return response;
    } catch (error) {
      console.error('Failed to update config:', error);
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-lg text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!backendConnected) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto mb-6"></div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Connecting to Automation Server</h2>
          <p className="text-gray-600 mb-6">
            {loading ? 'Connecting to backend server...' : 'Unable to connect to backend server'}
          </p>
          <div className="space-y-3">
            <p className="text-sm text-gray-500">
              Make sure the backend server is running on port 8002
            </p>
            <button
              onClick={loadConfig}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flexible-container bg-gray-50">
      <Toaster position="top-right" />
      
      <div className="h-screen">
        {/* Mobile backdrop */}
        {windowWidth < 768 && mobileMenuOpen && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-40"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}
        
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isCollapsed={sidebarCollapsed}
          setIsCollapsed={setSidebarCollapsed}
          windowWidth={windowWidth}
          mobileMenuOpen={mobileMenuOpen}
          setMobileMenuOpen={setMobileMenuOpen}
        />
        <main className={`h-screen overflow-auto bg-gray-50 transition-all duration-300 ${
          windowWidth < 768 
            ? 'ml-0' 
            : sidebarCollapsed 
              ? 'ml-16' 
              : 'ml-64'
        }`}>
          {/* Mobile menu button */}
          {windowWidth < 768 && (
            <div className="fixed top-4 left-4 z-40">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2 bg-white rounded-lg shadow-lg border border-gray-200 hover:bg-gray-50"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            </div>
          )}
          
          <div className="p-6">
            {activeTab === 'dashboard' && <Dashboard />}
            {activeTab === 'chat' && <AutomationChat />}
            {activeTab === 'actions' && <YourActions />}
            {activeTab === 'app-usage' && <AppUsage />}
            {activeTab === 'backend' && <BackendStatus backendConnected={backendConnected} />}
            {activeTab === 'smart-automation' && <SmartAutomation />}
            {activeTab === 'settings' && <Settings config={config} updateConfig={updateConfig} />}
            {activeTab === 'email' && <EmailConfig />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
