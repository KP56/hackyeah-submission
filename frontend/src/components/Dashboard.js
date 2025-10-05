import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSpring, animated, config } from '@react-spring/web';
import { 
  ClockIcon, 
  EyeIcon, 
  SparklesIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline';
import TimeSavedStatsModal from './TimeSavedStatsModal';

const Dashboard = () => {
  const [recentActions, setRecentActions] = useState([]);
  const [timeSaved, setTimeSaved] = useState(0);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [showTimeSavedStats, setShowTimeSavedStats] = useState(false);

  // Spring animation for time saved counter
  const timeSavedSpring = useSpring({
    number: timeSaved,
    from: { number: 0 },
    config: config.wobbly
  });

  useEffect(() => {
    loadRecentActions();
    loadTimeSavedData();
    const interval = setInterval(() => {
      loadRecentActions();
      loadTimeSavedData();
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const loadTimeSavedData = async () => {
    try {
      const data = await window.electronAPI.getTimeSavedStats();
      if (data.status === 'success') {
        setTimeSaved(data.stats.total_time_saved);
      }
    } catch (error) {
      console.error('Failed to load time saved data:', error);
    }
  };

  const loadRecentActions = async () => {
    try {
      console.log('Dashboard: Loading recent actions...');
      console.log('Dashboard: electronAPI available?', !!window.electronAPI);
      const data = await window.electronAPI.getActionRegistryAll(50);
      console.log('Dashboard: Received data:', data);
      setRecentActions(data.actions || []);
      setConnectionError(false);
    } catch (error) {
      console.error('Failed to load recent actions:', error);
      setConnectionError(true);
    } finally {
      setLoading(false);
    }
  };


  const getActionIcon = (action) => {
    // Handle general action types
    const actionType = action.action_type?.toLowerCase() || '';
    
    if (actionType.includes('file')) return '📄';
    if (actionType.includes('folder') || actionType.includes('directory')) return '📁';
    if (actionType.includes('keyboard') || actionType.includes('key')) return '⌨️';
    if (actionType.includes('mouse') || actionType.includes('click')) return '🖱️';
    if (actionType.includes('app') || actionType.includes('application')) return '💻';
    if (actionType.includes('automation') || actionType.includes('script')) return '🤖';
    if (actionType.includes('email') || actionType.includes('message')) return '📧';
    if (actionType.includes('web') || actionType.includes('browser')) return '🌐';
    if (actionType.includes('system') || actionType.includes('config')) return '⚙️';
    if (actionType.includes('edit') || actionType.includes('modify')) return '✏️';
    if (actionType.includes('create') || actionType.includes('new')) return '➕';
    if (actionType.includes('delete') || actionType.includes('remove')) return '🗑️';
    if (actionType.includes('move') || actionType.includes('copy')) return '📁';
    
    // Fallback for unknown action types
    return '📋';
  };

  const getActionColor = (action) => {
    const actionType = action.action_type?.toLowerCase() || '';
    
    if (actionType.includes('file')) return 'text-blue-600 bg-blue-50';
    if (actionType.includes('folder') || actionType.includes('directory')) return 'text-purple-600 bg-purple-50';
    if (actionType.includes('keyboard') || actionType.includes('key')) return 'text-indigo-600 bg-indigo-50';
    if (actionType.includes('mouse') || actionType.includes('click')) return 'text-pink-600 bg-pink-50';
    if (actionType.includes('app') || actionType.includes('application')) return 'text-green-600 bg-green-50';
    if (actionType.includes('automation') || actionType.includes('script')) return 'text-orange-600 bg-orange-50';
    if (actionType.includes('email') || actionType.includes('message')) return 'text-cyan-600 bg-cyan-50';
    if (actionType.includes('web') || actionType.includes('browser')) return 'text-teal-600 bg-teal-50';
    if (actionType.includes('system') || actionType.includes('config')) return 'text-gray-500 bg-gray-100';
    if (actionType.includes('edit') || actionType.includes('modify')) return 'text-blue-600 bg-blue-50';
    if (actionType.includes('create') || actionType.includes('new')) return 'text-green-600 bg-green-50';
    if (actionType.includes('delete') || actionType.includes('remove')) return 'text-red-600 bg-red-50';
    if (actionType.includes('move') || actionType.includes('copy')) return 'text-purple-600 bg-purple-50';
    
    // Default color for unknown action types
    return 'text-gray-600 bg-gray-50';
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
          <p className="text-gray-600">Monitor your automation and recent activities</p>
        </div>

        {/* Connection Error Display */}
        {connectionError && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4"
          >
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                <p className="text-sm text-red-600 mt-1">
                  Unable to connect to the backend server. Please check if the server is running.
                </p>
              </div>
            </div>
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Time Saved Card */}
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ 
              type: "spring", 
              stiffness: 300, 
              damping: 20,
              delay: 0.1 
            }}
            className="bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-lg p-6 text-white cursor-pointer hover:from-primary-600 hover:to-primary-700 hover:scale-105 hover:shadow-2xl transition-all duration-300"
            onClick={() => setShowTimeSavedStats(true)}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-primary-100 text-sm font-medium">Time Saved</p>
                <p className="text-3xl font-bold">
                  <animated.span>
                    {timeSavedSpring.number.to(n => n.toFixed(0))}
                  </animated.span>
                  <span> min</span>
                </p>
                <p className="text-primary-200 text-sm mt-1">Through automation</p>
              </div>
              <motion.div
                animate={{ 
                  scale: [1, 1.05, 1],
                  y: [0, -2, 0]
                }}
                transition={{ 
                  duration: 3, 
                  repeat: Infinity, 
                  ease: "easeInOut" 
                }}
              >
                <ClockIcon className="w-12 h-12 text-primary-200" />
              </motion.div>
            </div>
          </motion.div>

          {/* Recent Actions Card */}
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ 
              type: "spring", 
              stiffness: 300, 
              damping: 20,
              delay: 0.2 
            }}
            className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:scale-102 hover:shadow-lg transition-all duration-300"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                <EyeIcon className="w-5 h-5 mr-2" />
                Recent Actions
              </h2>
              <div className="text-sm text-gray-500">
                {recentActions.length} actions
              </div>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto scrollbar-always-visible" style={{
              scrollbarWidth: 'thin',
              scrollbarColor: '#d1d5db #f3f4f6',
              scrollbarGutter: 'stable'
            }}>
              <AnimatePresence mode="wait">
                {loading ? (
                  <motion.div 
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center justify-center py-8"
                  >
                    <motion.div 
                      className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    />
                  </motion.div>
                ) : recentActions.length === 0 ? (
                  <motion.div 
                    key="empty"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="text-center py-8 text-gray-500"
                  >
                    <motion.div
                      animate={{ 
                        scale: [1, 1.05, 1],
                        opacity: [0.7, 1, 0.7]
                      }}
                      transition={{ 
                        duration: 2, 
                        repeat: Infinity, 
                        ease: "easeInOut" 
                      }}
                    >
                      <ExclamationTriangleIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    </motion.div>
                    <p>No recent actions detected</p>
                    <p className="text-sm">Your actions will appear here</p>
                  </motion.div>
                ) : (
                  <div key="actions">
                    {recentActions.slice(0, 50).map((action, index) => (
                      <motion.div
                        key={action.id || index}
                        initial={{ opacity: 0, x: -20, scale: 0.95 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: 20, scale: 0.95 }}
                        transition={{ 
                          delay: index * 0.05,
                          type: "spring",
                          stiffness: 300,
                          damping: 20
                        }}
                        whileHover={{ 
                          scale: 1.02,
                          x: 5
                        }}
                        className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50 transition-all duration-200 cursor-pointer hover:bg-gray-100"
                        onClick={() => {
                          // Show action details in a modal or expand
                          console.log('Action details:', action);
                        }}
                      >
                        <motion.span 
                          className="text-lg"
                          animate={{ 
                            scale: [1, 1.1, 1],
                            y: [0, -1, 0]
                          }}
                          transition={{ 
                            duration: 0.6,
                            delay: index * 0.05,
                            ease: "easeInOut"
                          }}
                        >
                          {getActionIcon(action)}
                        </motion.span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {action.action_type || 'Unknown Action'}
                            </p>
                            {action.source && (
                              <span className="text-xs text-gray-500 bg-gray-200 px-1 rounded">
                                {action.source}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 truncate">
                            {action.details?.description || action.details?.src_path || 'No details available'}
                          </p>
                          {action.details?.dest_path && (
                            <p className="text-xs text-purple-600 truncate">
                              → {action.details.dest_path}
                            </p>
                          )}
                          <p className="text-xs text-gray-400">
                            {formatTimestamp(action.timestamp)}
                          </p>
                        </div>
                        <div className="flex flex-col items-end space-y-1">
                          <motion.span 
                            className={`px-2 py-1 text-xs font-medium rounded-full ${getActionColor(action)}`}
                            whileHover={{ scale: 1.1 }}
                          >
                            {action.action_type || 'Unknown'}
                          </motion.span>
                          {action.source && (
                            <span className="text-xs text-gray-400">
                              {action.source}
                            </span>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </div>

        {/* AI Status Card */}
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ 
            type: "spring", 
            stiffness: 300, 
            damping: 20,
            delay: 0.3 
          }}
          className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:scale-102 hover:shadow-lg transition-all duration-300"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <motion.div
                animate={{ 
                  scale: [1, 1.05, 1],
                  opacity: [0.8, 1, 0.8]
                }}
                transition={{ 
                  duration: 2, 
                  repeat: Infinity, 
                  ease: "easeInOut" 
                }}
              >
                <SparklesIcon className="w-6 h-6 text-primary-600 mr-3" />
              </motion.div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">AI Pattern Detection</h3>
                <p className="text-sm text-gray-600">Monitoring for automation opportunities</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <motion.div 
                className="w-2 h-2 bg-green-500 rounded-full"
                animate={{ 
                  scale: [1, 1.5, 1],
                  opacity: [1, 0.5, 1]
                }}
                transition={{ 
                  duration: 1.5, 
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />
              <motion.span 
                className="text-sm text-gray-600"
                animate={{ opacity: [0.7, 1, 0.7] }}
                transition={{ 
                  duration: 2, 
                  repeat: Infinity 
                }}
              >
                Active
              </motion.span>
            </div>
          </div>
        </motion.div>
      </div>
      
      {/* Time Saved Stats Modal */}
      <TimeSavedStatsModal 
        isOpen={showTimeSavedStats} 
        onClose={() => setShowTimeSavedStats(false)} 
      />
    </div>
  );
};

export default Dashboard;
