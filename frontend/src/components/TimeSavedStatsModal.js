import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  XMarkIcon, 
  ClockIcon, 
  ChartBarIcon,
  ArrowTrendingUpIcon,
  CalendarIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';

const TimeSavedStatsModal = ({ isOpen, onClose }) => {
  const [stats, setStats] = useState(null);
  const lastStatsRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [animationCompleted, setAnimationCompleted] = useState(false);
  const prevIsOpenRef = useRef(false);

  // Only reset animationCompleted when modal is opened (false -> true)
  useEffect(() => {
    if (isOpen && !prevIsOpenRef.current) {
      setAnimationCompleted(false);
    }
    prevIsOpenRef.current = isOpen;
  }, [isOpen]);

  // Always load stats when modal is open
  useEffect(() => {
    if (isOpen) {
      loadTimeSavedStats();
    }
  }, [isOpen]);

  const loadTimeSavedStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await window.electronAPI.getTimeSavedStats();
      if (data.status === 'success') {
        // Only update if daily_breakdown changed
        const newBreakdown = JSON.stringify(data.stats?.daily_breakdown || []);
        const lastBreakdown = JSON.stringify(lastStatsRef.current?.daily_breakdown || []);
        if (newBreakdown !== lastBreakdown) {
          setStats(data.stats);
          lastStatsRef.current = data.stats;
        }
      } else {
        setError(data.message || 'Failed to load time saved statistics');
      }
    } catch (err) {
      console.error('Failed to load time saved stats:', err);
      setError('Failed to load time saved statistics');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (minutes) => {
    if (minutes < 60) {
      return `${minutes.toFixed(1)} min`;
    } else {
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;
      return `${hours}h ${remainingMinutes.toFixed(0)}m`;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const getEfficiencyColor = (efficiency) => {
    if (efficiency >= 80) return 'text-green-600';
    if (efficiency >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getEfficiencyBgColor = (efficiency) => {
    if (efficiency >= 80) return 'bg-green-50';
    if (efficiency >= 60) return 'bg-yellow-50';
    return 'bg-red-50';
  };

  // Line chart component
  const LineChart = ({ data, width = 400, height = 200, animationCompleted, onAnimationComplete }) => {
    if (!data || data.length === 0) return null;

    // Use actual backend data, sorted by date
    const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
    const maxValue = Math.max(...sortedData.map(d => d.time_saved));
    const minValue = Math.min(...sortedData.map(d => d.time_saved));
    const range = maxValue - minValue || 1;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    const points = sortedData.map((d, index) => {
      const x = padding + (index / (sortedData.length - 1)) * chartWidth;
      const y = padding + chartHeight - ((d.time_saved - minValue) / range) * chartHeight;
      return { x, y, data: d };
    });

    const pathData = points.map((point, index) => {
      const command = index === 0 ? 'M' : 'L';
      return `${command} ${point.x} ${point.y}`;
    }).join(' ');

    return (
      <div className="relative">
        <svg width={width} height={height} className="overflow-visible">
          {/* Grid lines */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f3f4f6" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          
          {/* Line chart */}
          <motion.path
            initial={{ pathLength: animationCompleted ? 1 : 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: animationCompleted ? 0 : 2, ease: "easeInOut" }}
            onAnimationComplete={() => {
              if (!animationCompleted && onAnimationComplete) {
                onAnimationComplete();
              }
            }}
            d={pathData}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          
          {/* Data points */}
          {points.map((point, index) => (
            <motion.circle
              key={index}
              initial={{ scale: animationCompleted ? 1 : 0, opacity: animationCompleted ? 1 : 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ 
                delay: animationCompleted ? 0 : index * 0.05, 
                duration: animationCompleted ? 0 : 0.3 
              }}
              cx={point.x}
              cy={point.y}
              r="4"
              fill="#3b82f6"
              className="hover:r-6 transition-all cursor-pointer"
            >
              <title>{`${formatDate(point.data.date)}: ${formatTime(point.data.time_saved)}`}</title>
            </motion.circle>
          ))}
          
          {/* Y-axis labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, index) => {
            const value = minValue + range * (1 - ratio);
            const y = padding + chartHeight * ratio;
            return (
              <g key={index}>
                <line x1={padding - 5} y1={y} x2={padding} y2={y} stroke="#6b7280" strokeWidth="1"/>
                <text x={padding - 10} y={y + 4} textAnchor="end" className="text-xs fill-gray-600">
                  {formatTime(value)}
                </text>
              </g>
            );
          })}
          
          {/* X-axis labels */}
          {data.filter((_, index) => index % 5 === 0).map((d, index) => {
            const x = padding + (index * 5 / (data.length - 1)) * chartWidth;
            return (
              <g key={index}>
                <line x1={x} y1={height - padding} x2={x} y2={height - padding + 5} stroke="#6b7280" strokeWidth="1"/>
                <text x={x} y={height - padding + 18} textAnchor="middle" className="text-xs fill-gray-600">
                  {formatDate(d.date)}
                </text>
              </g>
            );
          })}
        </svg>
        
        {/* Chart title */}
        <div className="absolute top-2 left-2 text-sm font-medium text-gray-700">
          Time Saved Trend (30 Days)
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-4 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <motion.div
                  animate={{ 
                    rotate: [0, 5, -5, 0],
                    scale: [1, 1.05, 1]
                  }}
                  transition={{ 
                    duration: 2, 
                    repeat: Infinity, 
                    ease: "easeInOut" 
                  }}
                >
                  <ClockIcon className="w-8 h-8" />
                </motion.div>
                <div>
                  <h2 className="text-xl font-bold">Time Saved Statistics</h2>
                  <p className="text-primary-100 text-sm">Automation efficiency insights</p>
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-2 hover:bg-primary-700 rounded-lg transition-colors"
              >
                <XMarkIcon className="w-6 h-6" />
              </motion.button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <motion.div 
                  className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <div className="text-red-500 mb-4">
                  <XMarkIcon className="w-16 h-16 mx-auto" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Statistics</h3>
                <p className="text-gray-600 mb-4">{error}</p>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={loadTimeSavedStats}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                >
                  Try Again
                </motion.button>
              </div>
            ) : stats ? (
              <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200"
                  >
                    <div className="flex items-center space-x-3">
                      <ClockIcon className="w-8 h-8 text-blue-600" />
                      <div>
                        <p className="text-sm text-blue-600 font-medium">Total Time Saved</p>
                        <p className="text-2xl font-bold text-blue-900">
                          {formatTime(stats.total_time_saved)}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200"
                  >
                    <div className="flex items-center space-x-3">
                      <SparklesIcon className="w-8 h-8 text-purple-600" />
                      <div>
                        <p className="text-sm text-purple-600 font-medium">AI Interactions</p>
                        <p className="text-2xl font-bold text-purple-900">
                          {stats.ai_interactions_count}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                </div>

                {/* Daily Breakdown Line Chart */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="bg-white border border-gray-200 rounded-lg p-6"
                >
                  <div className="flex items-center space-x-2 mb-4">
                    <CalendarIcon className="w-6 h-6 text-gray-600" />
                    <h3 className="text-lg font-semibold text-gray-900">Time Saved Trend</h3>
                  </div>
                  
                  <div className="flex justify-center">
                    <LineChart 
                      data={[...stats.daily_breakdown].sort((a, b) => new Date(a.date) - new Date(b.date))} 
                      width={600} 
                      height={300}
                      animationCompleted={true}
                      onAnimationComplete={() => {}}
                    />
                  </div>
                  
                  {/* Summary stats below chart */}
                  {/* Removed starting/ending value display */}
                </motion.div>

                {/* Predictions */}
                {stats.predictions && stats.predictions.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="bg-white border border-gray-200 rounded-lg p-6"
                  >
                    <div className="flex items-center space-x-2 mb-4">
                      <ArrowTrendingUpIcon className="w-6 h-6 text-green-600" />
                      <h3 className="text-lg font-semibold text-gray-900">Future Predictions (Next 7 Days)</h3>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {stats.predictions.map((prediction, index) => (
                        <motion.div
                          key={prediction.date}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.7 + index * 0.1 }}
                          className="bg-gradient-to-br from-green-50 to-green-100 p-3 rounded-lg border border-green-200"
                        >
                          <div className="text-sm text-green-600 font-medium">
                            {formatDate(prediction.date)}
                          </div>
                          <div className="text-lg font-bold text-green-900">
                            {formatTime(prediction.predicted_time_saved)}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* Operation Breakdown */}
                {stats.operation_counts && Object.keys(stats.operation_counts).length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 }}
                    className="bg-white border border-gray-200 rounded-lg p-6"
                  >
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Operation Breakdown</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Object.entries(stats.operation_counts).map(([operation, count], index) => (
                        <motion.div
                          key={operation}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.9 + index * 0.1 }}
                          className="text-center p-3 bg-gray-50 rounded-lg"
                        >
                          <div className="text-sm text-gray-600 capitalize">
                            {operation.replace('_', ' ')}
                          </div>
                          <div className="text-xl font-bold text-gray-900">
                            {count}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>
            ) : null}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default TimeSavedStatsModal;
