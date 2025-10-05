import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  ClockIcon,
  CalendarIcon,
  SparklesIcon,
  ChartBarIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';

const SmartAutomation = () => {
  const [actionStats, setActionStats] = useState(null);
  const [allSuggestions, setAllSuggestions] = useState([]);
  const [longTermStatus, setLongTermStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [statsData, suggestionsData, longTermData] = await Promise.all([
        window.electronAPI.getActionRegistryStats(),
        window.electronAPI.getAllSuggestions(),
        window.electronAPI.getLongTermStatus()
      ]);

      setActionStats(statsData);
      setAllSuggestions(suggestionsData.suggestions || []);
      setLongTermStatus(longTermData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircleIcon className="w-5 h-5 text-red-500" />;
      case 'executing':
        return <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>;
      default:
        return <ExclamationCircleIcon className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      accepted: 'bg-blue-100 text-blue-800',
      explained: 'bg-purple-100 text-purple-800',
      executing: 'bg-orange-100 text-orange-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      rejected: 'bg-gray-100 text-gray-800'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.pending}`}>
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center">
            <SparklesIcon className="w-8 h-8 mr-3 text-primary-600" />
            Smart Automation System
          </h1>
          <p className="text-gray-600">
            Intelligent pattern detection and automation workflow
          </p>
        </div>

        {/* Three-Part System Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Part 1: Action Registry */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mr-4">
                  <ChartBarIcon className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Action Registry</h3>
                  <p className="text-sm text-gray-500">Central action storage</p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {actionStats && !actionStats.error ? (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Total Actions:</span>
                    <span className="text-lg font-bold text-gray-900">{actionStats.total_actions}</span>
                  </div>
                  
                  {actionStats.action_types && Object.keys(actionStats.action_types).length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-gray-700 mb-2">Action Types:</p>
                      <div className="space-y-1">
                        {Object.entries(actionStats.action_types).map(([type, count]) => (
                          <div key={type} className="flex justify-between text-xs">
                            <span className="text-gray-600">{type}:</span>
                            <span className="font-medium text-gray-900">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {actionStats.sources && Object.keys(actionStats.sources).length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-gray-700 mb-2">Sources:</p>
                      <div className="space-y-1">
                        {Object.entries(actionStats.sources).map(([source, count]) => (
                          <div key={source} className="flex justify-between text-xs">
                            <span className="text-gray-600">{source}:</span>
                            <span className="font-medium text-gray-900">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-gray-500">No action data available</p>
              )}
            </div>
          </motion.div>

          {/* Part 2: Short-Term Pattern Detection */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mr-4">
                  <ClockIcon className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Short-Term Patterns</h3>
                  <p className="text-sm text-gray-500">10-20 second detection</p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Total Suggestions:</span>
                <span className="text-lg font-bold text-gray-900">{allSuggestions.length}</span>
              </div>

              <div className="grid grid-cols-2 gap-2 mt-4">
                <div className="bg-green-50 rounded-lg p-3">
                  <p className="text-xs text-gray-600 mb-1">Completed</p>
                  <p className="text-xl font-bold text-green-600">
                    {allSuggestions.filter(s => s.status === 'completed').length}
                  </p>
                </div>
                <div className="bg-yellow-50 rounded-lg p-3">
                  <p className="text-xs text-gray-600 mb-1">Pending</p>
                  <p className="text-xl font-bold text-yellow-600">
                    {allSuggestions.filter(s => s.status === 'pending').length}
                  </p>
                </div>
              </div>

              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-blue-800">
                  ✨ Actively monitoring your actions for automation opportunities
                </p>
              </div>
            </div>
          </motion.div>

          {/* Part 3: Long-Term Pattern Detection */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mr-4">
                  <CalendarIcon className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Long-Term Patterns</h3>
                  <p className="text-sm text-gray-500">Days/weeks analysis</p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {longTermStatus?.status === 'coming_soon' ? (
                <>
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
                    <p className="text-sm font-medium text-purple-900 mb-2">
                      🚀 Coming Soon!
                    </p>
                    <p className="text-xs text-purple-700">
                      {longTermStatus.message}
                    </p>
                  </div>

                  {longTermStatus.planned_features && (
                    <div>
                      <p className="text-xs font-medium text-gray-700 mb-2">Planned Features:</p>
                      <ul className="space-y-1">
                        {longTermStatus.planned_features.map((feature, index) => (
                          <li key={index} className="text-xs text-gray-600 flex items-start">
                            <span className="text-purple-500 mr-2">•</span>
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-gray-500">Long-term pattern detection active</p>
              )}
            </div>
          </motion.div>
        </div>

        {/* Automation History */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl shadow-sm border border-gray-200"
        >
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center">
              <SparklesIcon className="w-6 h-6 mr-2 text-primary-600" />
              Automation History
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              All automation suggestions and their status
            </p>
          </div>

          <div className="divide-y divide-gray-200 max-h-[500px] overflow-y-auto">
            {allSuggestions.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <SparklesIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No automation suggestions yet</p>
                <p className="text-sm mt-2">Start performing repetitive actions to get suggestions</p>
              </div>
            ) : (
              allSuggestions.map((suggestion, index) => (
                <div key={suggestion.suggestion_id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4 flex-1">
                      <div className="flex-shrink-0 mt-1">
                        {getStatusIcon(suggestion.status)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          {getStatusBadge(suggestion.status)}
                          <span className="text-xs text-gray-500">
                            {formatTimestamp(suggestion.timestamp)}
                          </span>
                        </div>
                        <p className="text-sm text-gray-900 font-medium mb-2">
                          {suggestion.pattern_description}
                        </p>
                        {suggestion.user_explanation && (
                          <div className="bg-blue-50 rounded-lg p-3 mb-2">
                            <p className="text-xs font-medium text-blue-900 mb-1">User Request:</p>
                            <p className="text-xs text-blue-700">{suggestion.user_explanation}</p>
                          </div>
                        )}
                        {suggestion.execution_result && (
                          <div className="mt-2">
                            <p className="text-xs text-gray-600">
                              Attempts: {suggestion.execution_result.attempts?.length || 0} | 
                              Success: {suggestion.execution_result.success ? 'Yes' : 'No'}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default SmartAutomation;

