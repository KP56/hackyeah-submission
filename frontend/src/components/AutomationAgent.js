import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { 
  CogIcon, 
  PlayIcon, 
  StopIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';

const AutomationAgent = () => {
  const [patterns, setPatterns] = useState([]);
  const [selectedPattern, setSelectedPattern] = useState(null);
  const [automationPlan, setAutomationPlan] = useState('');
  const [generatedScript, setGeneratedScript] = useState('');
  const [executionHistory, setExecutionHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [showScriptModal, setShowScriptModal] = useState(false);

  useEffect(() => {
    loadPatterns();
    loadExecutionHistory();
    const interval = setInterval(() => {
      loadPatterns();
      loadExecutionHistory();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadPatterns = async () => {
    try {
      const data = await window.electronAPI.getPatterns();
      setPatterns(data.patterns || []);
      if (data.patterns?.length > 0 && !selectedPattern) {
        setSelectedPattern(data.patterns[0]);
      }
    } catch (error) {
      console.error('Failed to load patterns:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadExecutionHistory = async () => {
    try {
      const data = await window.electronAPI.getExecutionHistory();
      setExecutionHistory(data.executions || []);
    } catch (error) {
      console.error('Failed to load execution history:', error);
    }
  };

  const generateAutomationPlan = async (pattern) => {
    if (!pattern) return;
    
    setGenerating(true);
    try {
      const data = await window.electronAPI.generateAutomationPlan(pattern.description);
      setAutomationPlan(data.plan || '');
      toast.success('Automation plan generated!');
    } catch (error) {
      console.error('Failed to generate automation plan:', error);
      toast.error('Failed to generate automation plan');
    } finally {
      setGenerating(false);
    }
  };

  const generateScript = async (pattern) => {
    if (!pattern) return;
    
    setGenerating(true);
    try {
      const data = await window.electronAPI.generateScript(pattern.description);
      setGeneratedScript(data.script || '');
      setShowScriptModal(true);
      toast.success('Script generated!');
    } catch (error) {
      console.error('Failed to generate script:', error);
      toast.error('Failed to generate script');
    } finally {
      setGenerating(false);
    }
  };

  const executeScript = async (script) => {
    setExecuting(true);
    try {
      const data = await window.electronAPI.executeScript(script);
      toast.success('Script executed successfully!');
      loadExecutionHistory();
    } catch (error) {
      console.error('Failed to execute script:', error);
      toast.error('Failed to execute script');
    } finally {
      setExecuting(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  };

  const getExecutionStatusIcon = (status) => {
    switch (status) {
      case 'success': return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'error': return <XCircleIcon className="w-5 h-5 text-red-500" />;
      default: return <ClockIcon className="w-5 h-5 text-yellow-500" />;
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Automation Agent</h1>
          <p className="text-gray-600">Detect patterns and create automation workflows</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Patterns List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <SparklesIcon className="w-5 h-5 mr-2" />
                  Detected Patterns
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  {patterns.length} patterns detected
                </p>
              </div>

              <div className="max-h-96 overflow-y-auto">
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                  </div>
                ) : patterns.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <CogIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>No patterns detected yet</p>
                    <p className="text-sm">Patterns will appear here when detected</p>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {patterns.map((pattern, index) => (
                      <motion.button
                        key={index}
                        onClick={() => setSelectedPattern(pattern)}
                        className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                          selectedPattern === pattern ? 'bg-primary-50 border-r-2 border-primary-500' : ''
                        }`}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <div className="flex items-start space-x-3">
                          <div className="flex-shrink-0">
                            <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                              <CogIcon className="w-4 h-4 text-primary-600" />
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 mb-1 line-clamp-2">
                              {pattern.description}
                            </p>
                            <p className="text-xs text-gray-500 flex items-center">
                              <ClockIcon className="w-3 h-3 mr-1" />
                              {formatTimestamp(pattern.timestamp)}
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

          {/* Pattern Details and Actions */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-full">
              {selectedPattern ? (
                <div className="h-full flex flex-col">
                  <div className="p-6 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                      <DocumentTextIcon className="w-5 h-5 mr-2" />
                      Pattern Details
                    </h2>
                    <p className="text-sm text-gray-600 mt-1">
                      {formatTimestamp(selectedPattern.timestamp)}
                    </p>
                  </div>

                  <div className="flex-1 flex flex-col">
                    {/* Pattern Description */}
                    <div className="p-6 border-b border-gray-200">
                      <h3 className="text-sm font-medium text-gray-700 mb-3">Pattern Description</h3>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-sm text-gray-900 whitespace-pre-wrap">
                          {selectedPattern.description}
                        </p>
                      </div>
                    </div>

                    {/* Automation Plan */}
                    <div className="p-6 border-b border-gray-200">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-medium text-gray-700">Automation Plan</h3>
                        <button
                          onClick={() => generateAutomationPlan(selectedPattern)}
                          disabled={generating}
                          className="px-3 py-1 text-xs bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {generating ? 'Generating...' : 'Generate Plan'}
                        </button>
                      </div>
                      <div className="bg-blue-50 rounded-lg p-4 min-h-32">
                        {automationPlan ? (
                          <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono">
                            {automationPlan}
                          </pre>
                        ) : (
                          <p className="text-sm text-gray-500 italic">
                            Click "Generate Plan" to create an automation plan for this pattern
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="p-6">
                      <div className="flex space-x-4">
                        <button
                          onClick={() => generateScript(selectedPattern)}
                          disabled={generating}
                          className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <CodeBracketIcon className="w-4 h-4 mr-2" />
                          {generating ? 'Generating...' : 'Generate Script'}
                        </button>
                        
                        <button
                          onClick={() => setShowScriptModal(true)}
                          disabled={!generatedScript}
                          className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <DocumentTextIcon className="w-4 h-4 mr-2" />
                          View Script
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500">
                  <div className="text-center">
                    <CogIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>Select a pattern to view details and create automation</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Execution History */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200"
        >
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center">
              <PlayIcon className="w-5 h-5 mr-2" />
              Execution History
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {executionHistory.length} executions
            </p>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {executionHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <PlayIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No executions yet</p>
                <p className="text-sm">Script executions will appear here</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {executionHistory.map((execution, index) => (
                  <div key={index} className="p-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        {getExecutionStatusIcon(execution.status)}
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {execution.script_name || 'Unnamed Script'}
                          </p>
                          <p className="text-xs text-gray-500">
                            {formatTimestamp(execution.timestamp)}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-500">
                          Status: {execution.status}
                        </p>
                        {execution.duration && (
                          <p className="text-xs text-gray-500">
                            Duration: {execution.duration}ms
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>

        {/* Script Modal */}
        <AnimatePresence>
          {showScriptModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
              onClick={() => setShowScriptModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] flex flex-col"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b border-gray-200 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">Generated Script</h3>
                  <button
                    onClick={() => setShowScriptModal(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <XCircleIcon className="w-6 h-6" />
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-6">
                  <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono bg-gray-50 p-4 rounded-lg">
                    {generatedScript}
                  </pre>
                </div>
                
                <div className="p-6 border-t border-gray-200 flex justify-end space-x-4">
                  <button
                    onClick={() => setShowScriptModal(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300"
                  >
                    Close
                  </button>
                  <button
                    onClick={() => {
                      executeScript(generatedScript);
                      setShowScriptModal(false);
                    }}
                    disabled={executing}
                    className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {executing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Executing...
                      </>
                    ) : (
                      <>
                        <PlayIcon className="w-4 h-4 mr-2" />
                        Execute Script
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AutomationAgent;
