import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  SparklesIcon, 
  ClockIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon 
} from '@heroicons/react/24/outline';

const AI = () => {
  const [interactions, setInteractions] = useState([]);
  const [automations, setAutomations] = useState([]);
  const [selectedInteraction, setSelectedInteraction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [activeTab, setActiveTab] = useState('interactions');

  useEffect(() => {
    loadInteractions();
    loadAutomations();
    const interval = setInterval(() => {
      loadInteractions();
      loadAutomations();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadInteractions = async () => {
    try {
      const data = await window.electronAPI.getAIInteractions();
      setInteractions(data.interactions || []);
      setConnectionError(false);
      if (data.interactions?.length > 0 && !selectedInteraction && interactions.length === 0) {
        setSelectedInteraction(data.interactions[0]);
      }
    } catch (error) {
      console.error('Failed to load AI interactions:', error);
      setConnectionError(true);
    } finally {
      setLoading(false);
    }
  };

  const loadAutomations = async () => {
    try {
      const data = await window.electronAPI.getAutomationHistory();
      setAutomations(data.automations || []);
    } catch (error) {
      console.error('Failed to load automation history:', error);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const truncateText = (text, maxLength = 60) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Interactions</h1>
          <p className="text-gray-600">Monitor and review AI prompts, responses, and automation history</p>
          
          {/* Tabs */}
          <div className="mt-6 border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('interactions')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'interactions'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <ChatBubbleLeftRightIcon className="w-4 h-4 inline mr-2" />
                AI Interactions ({interactions.length})
              </button>
              <button
                onClick={() => setActiveTab('automations')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'automations'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <SparklesIcon className="w-4 h-4 inline mr-2" />
                Automation History ({automations.length})
              </button>
            </nav>
          </div>
        </div>

        {/* Connection Error Display */}
        {connectionError && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                <p className="text-sm text-red-600 mt-1">
                  Unable to load AI interactions. Please check if the backend server is running.
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Interactions Tab */}
        {activeTab === 'interactions' && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Interactions List */}
              <div className="lg:col-span-1">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                  <div className="p-6 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                      <ChatBubbleLeftRightIcon className="w-5 h-5 mr-2" />
                      Recent Interactions
                    </h2>
                    <p className="text-sm text-gray-600 mt-1">
                      {interactions.length} total interactions
                    </p>
                  </div>

                  <div className="max-h-96 overflow-y-auto">
                    {loading ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                      </div>
                    ) : interactions.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <SparklesIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                        <p>No AI interactions yet</p>
                        <p className="text-sm">Interactions will appear here when AI is used</p>
                      </div>
                    ) : (
                      <div className="divide-y divide-gray-200">
                        {interactions.map((interaction, index) => (
                          <motion.button
                            key={index}
                            onClick={() => setSelectedInteraction(interaction)}
                            className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                              selectedInteraction === interaction ? 'bg-primary-50 border-r-2 border-primary-500' : ''
                            }`}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                          >
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                                  <SparklesIcon className="w-4 h-4 text-primary-600" />
                                </div>
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 mb-1">
                                  {truncateText(interaction.prompt)}
                                </p>
                                <p className="text-xs text-gray-500 flex items-center">
                                  <ClockIcon className="w-3 h-3 mr-1" />
                                  {formatTimestamp(interaction.timestamp)}
                                </p>
                              </div>
                            </div>
                          </motion.button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Interaction Details */}
              <div className="lg:col-span-2">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-full">
                  {selectedInteraction ? (
                    <div className="h-full flex flex-col">
                      <div className="p-6 border-b border-gray-200">
                        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                          <DocumentTextIcon className="w-5 h-5 mr-2" />
                          Interaction Details
                        </h2>
                        <p className="text-sm text-gray-600 mt-1">
                          {formatTimestamp(selectedInteraction.timestamp)}
                        </p>
                      </div>

                      <div className="flex-1 flex flex-col">
                        {/* Prompt Section */}
                        <div className="p-6 border-b border-gray-200">
                          <h3 className="text-sm font-medium text-gray-700 mb-3">Prompt</h3>
                          <div className="bg-gray-50 rounded-lg p-4">
                            <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono">
                              {selectedInteraction.prompt}
                            </pre>
                          </div>
                        </div>

                        {/* Response Section */}
                        <div className="p-6 flex-1">
                          <h3 className="text-sm font-medium text-gray-700 mb-3">Response</h3>
                          <div className="bg-blue-50 rounded-lg p-4 h-full">
                            <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono h-full overflow-y-auto">
                              {selectedInteraction.response}
                            </pre>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-gray-500">
                      <div className="text-center">
                        <SparklesIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                        <p>Select an interaction to view details</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Stats Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary-600">{interactions.length}</div>
                  <div className="text-sm text-gray-600">Total Interactions</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {interactions.filter(i => i.response && i.response.length > 0).length}
                  </div>
                  <div className="text-sm text-gray-600">Successful Responses</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {interactions.length > 0 ? Math.round(interactions.reduce((acc, i) => acc + i.prompt.length, 0) / interactions.length) : 0}
                  </div>
                  <div className="text-sm text-gray-600">Avg Prompt Length</div>
                </div>
              </div>
            </motion.div>
          </>
        )}

        {/* Automations Tab */}
        {activeTab === 'automations' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <SparklesIcon className="w-5 h-5 mr-2" />
              Automation History
            </h2>
            {automations.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <SparklesIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No automations yet</p>
                <p className="text-sm">Automations will appear here when triggered</p>
              </div>
            ) : (
              <div className="space-y-4">
                {automations.map((automation, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">{automation.name}</h3>
                        <p className="text-sm text-gray-600">{automation.description}</p>
                      </div>
                      <div className="text-sm text-gray-500">
                        {formatTimestamp(automation.timestamp)}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AI;
