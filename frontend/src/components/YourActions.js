import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClockIcon,
  FolderIcon,
  DocumentIcon,
  ArrowPathIcon,
  TrashIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';

const YourActions = () => {
  const [actions, setActions] = useState([]);
  const [minuteSummaries, setMinuteSummaries] = useState([]);
  const [tenMinuteSummaries, setTenMinuteSummaries] = useState([]);
  const [stats, setStats] = useState({
    total_actions: 0,
    action_types_count: {},
    sources_count: {}
  });
  const [currentActivity, setCurrentActivity] = useState({
    current_app: null,
    current_window: null,
    recent_keys: [],
    recent_app_switches: [],
    keyboard_sequence: ""
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAllData();

    const interval = setInterval(() => {
      loadAllData();
    }, 2000); // Refresh every 2 seconds

    return () => clearInterval(interval);
  }, []);

  const loadAllData = async () => {
    try {
      // Load all data in parallel
      await Promise.all([
        loadActions(),
        loadStats(),
        loadCurrentActivity(),
        loadMinuteSummaries(),
        loadTenMinuteSummaries()
      ]);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };

  const loadActions = async () => {
    try {
      const data = await window.electronAPI.getActionRegistryAll(50); // Get last 50 actions
      setActions(data.actions || []);
    } catch (error) {
      console.error('Failed to load actions:', error);
    }
  };

  const loadStats = async () => {
    try {
      const data = await window.electronAPI.getActionRegistryStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadCurrentActivity = async () => {
    try {
      const data = await window.electronAPI.getCurrentActivity();
      setCurrentActivity(data);
    } catch (error) {
      console.error('Failed to load current activity:', error);
    }
  };

  const loadMinuteSummaries = async () => {
    try {
      const data = await window.electronAPI.getMinuteSummaries(100);
      setMinuteSummaries(data.summaries || []);
    } catch (error) {
      console.error('Failed to load minute summaries:', error);
    }
  };

  const loadTenMinuteSummaries = async () => {
    try {
      const data = await window.electronAPI.getTenMinuteSummaries(100);
      setTenMinuteSummaries(data.summaries || []);
    } catch (error) {
      console.error('Failed to load ten-minute summaries:', error);
    }
  };

  const deleteMinuteSummary = async (summaryId) => {
    try {
      await window.electronAPI.deleteMinuteSummary(summaryId);
      // Reload summaries after deletion
      loadMinuteSummaries();
    } catch (error) {
      console.error('Failed to delete minute summary:', error);
    }
  };

  const deleteTenMinuteSummary = async (summaryId) => {
    try {
      await window.electronAPI.deleteTenMinuteSummary(summaryId);
      // Reload summaries after deletion
      loadTenMinuteSummaries();
    } catch (error) {
      console.error('Failed to delete ten-minute summary:', error);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleString();
  };

  const getActionIcon = (type) => {
    if (type.includes('file')) return <DocumentIcon className="w-5 h-5" />;
    if (type.includes('folder')) return <FolderIcon className="w-5 h-5" />;
    return <ArrowPathIcon className="w-5 h-5" />;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Your Activity Timeline</h1>
          <p className="text-gray-600">Track your actions and AI-generated summaries</p>
        </motion.div>

        {/* Current Activity Card */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-2xl p-6 shadow-lg border-2 border-purple-200 mb-8"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <h2 className="text-xl font-bold text-gray-900">Live Activity Monitor</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Current Application */}
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <p className="text-sm font-semibold text-gray-500 mb-2">CURRENT APPLICATION</p>
              {currentActivity.current_app ? (
                <>
                  <p className="text-2xl font-bold text-purple-600 mb-1">{currentActivity.current_app}</p>
                  <p className="text-sm text-gray-600 truncate">{currentActivity.current_window || 'No window title'}</p>
                </>
              ) : (
                <p className="text-gray-400 italic">No active application detected</p>
              )}
            </div>

            {/* Recent Keys */}
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <p className="text-sm font-semibold text-gray-500 mb-2">RECENT KEYSTROKES</p>
              {currentActivity.recent_keys && currentActivity.recent_keys.length > 0 ? (
                <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                  {currentActivity.recent_keys.map((key, index) => (
                    <span 
                      key={index}
                      className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded border border-gray-300 font-mono"
                    >
                      {key}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 italic">No recent keystrokes</p>
              )}
            </div>
          </div>
        </motion.div>

        {/* 3-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Recent Actions */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <ArrowPathIcon className="w-6 h-6 text-blue-600" />
                <h2 className="text-xl font-bold text-gray-900">Recent Actions</h2>
              </div>
              <span className="text-sm font-semibold text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                {actions.length}
              </span>
            </div>
            
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {actions.length === 0 ? (
                <div className="text-center py-12">
                  <ArrowPathIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No actions yet</p>
                  <p className="text-sm text-gray-400 mt-2">Start working and we'll track your actions!</p>
                </div>
              ) : (
                actions.map((action, index) => (
                  <motion.div
                    key={action.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.01 }}
                    className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                  >
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                      {getActionIcon(action.action_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 text-sm">{action.action_type}</p>
                      <p className="text-xs text-gray-500 truncate">
                        {action.details?.src_path || action.details?.description || 'No details'}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">{formatTimestamp(action.timestamp)}</p>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>

          {/* Middle Column: 1-Minute Summaries */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <ClockIcon className="w-6 h-6 text-green-600" />
                <h2 className="text-xl font-bold text-gray-900">1-Minute Summaries</h2>
              </div>
              <span className="text-sm font-semibold text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                {minuteSummaries.length}
              </span>
            </div>
            
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {minuteSummaries.length === 0 ? (
                <div className="text-center py-12">
                  <SparklesIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No summaries yet</p>
                  <p className="text-sm text-gray-400 mt-2">AI will generate summaries every minute</p>
                </div>
              ) : (
                minuteSummaries.map((summary, index) => (
                  <motion.div
                    key={summary.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.01 }}
                    className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-200 hover:shadow-md transition-all group relative"
                  >
                    <button
                      onClick={() => deleteMinuteSummary(summary.id)}
                      className="absolute top-2 right-2 p-1 bg-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50"
                      title="Delete summary"
                    >
                      <TrashIcon className="w-4 h-4 text-red-600" />
                    </button>
                    
                    <p className="text-sm text-gray-800 mb-2 pr-8">{summary.summary}</p>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{formatTimestamp(summary.timestamp)}</span>
                      <span className="bg-white px-2 py-1 rounded">{summary.action_count} actions</span>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>

          {/* Right Column: 10-Minute Summaries */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <SparklesIcon className="w-6 h-6 text-purple-600" />
                <h2 className="text-xl font-bold text-gray-900">10-Minute Summaries</h2>
              </div>
              <span className="text-sm font-semibold text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                {tenMinuteSummaries.length}
              </span>
            </div>
            
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {tenMinuteSummaries.length === 0 ? (
                <div className="text-center py-12">
                  <SparklesIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No summaries yet</p>
                  <p className="text-sm text-gray-400 mt-2">AI will generate summaries every 10 minutes</p>
                </div>
              ) : (
                tenMinuteSummaries.map((summary, index) => (
                  <motion.div
                    key={summary.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.01 }}
                    className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200 hover:shadow-md transition-all group relative"
                  >
                    <button
                      onClick={() => deleteTenMinuteSummary(summary.id)}
                      className="absolute top-2 right-2 p-1 bg-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50"
                      title="Delete summary"
                    >
                      <TrashIcon className="w-4 h-4 text-red-600" />
                    </button>
                    
                    <p className="text-sm text-gray-800 mb-2 pr-8 whitespace-pre-wrap">{summary.summary}</p>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{formatTimestamp(summary.timestamp)}</span>
                      <span className="bg-white px-2 py-1 rounded">{summary.total_actions} actions</span>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        </div>

        {/* Stats Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Total Actions</p>
                <p className="text-3xl font-bold text-gray-900">{stats.total_actions}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <ArrowPathIcon className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Minute Summaries</p>
                <p className="text-3xl font-bold text-gray-900">{minuteSummaries.length}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <ClockIcon className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">10-Minute Summaries</p>
                <p className="text-3xl font-bold text-gray-900">{tenMinuteSummaries.length}</p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                <SparklesIcon className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default YourActions;
