import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ComputerDesktopIcon,
  ClockIcon,
  ChartBarIcon,
  CalendarIcon,
  ArrowTrendingUpIcon,
  ChartPieIcon
} from '@heroicons/react/24/outline';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  LineChart,
  Line,
  AreaChart,
  Area,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const AppUsage = () => {
  const [todayUsage, setTodayUsage] = useState({ usage: {}, total_minutes: 0 });
  const [weekUsage, setWeekUsage] = useState({});
  const [hourlyUsage, setHourlyUsage] = useState({});
  const [stats, setStats] = useState(null);
  const [viewMode, setViewMode] = useState('today'); // 'today', 'week', 'hourly'
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      const [todayRes, weekRes, statsRes] = await Promise.all([
        window.electronAPI.getAppUsageToday(),
        window.electronAPI.getAppUsageWeek(),
        window.electronAPI.getAppUsageStats()
      ]);

      console.log('📊 Received app usage data:', { todayRes, weekRes, statsRes });

      setTodayUsage(todayRes);
      const weekData = weekRes.week_usage || {};
      setWeekUsage(weekData);
      
      // Build hourly data from the entire week
      const allHourlyData = {};
      Object.keys(weekData).sort().reverse().slice(0, 7).forEach(date => {
        // For each day, try to get hourly data
        window.electronAPI.getAppUsageHourly(date).then(hourlyRes => {
          const hourlyForDay = hourlyRes.hourly_usage || {};
          Object.keys(hourlyForDay).forEach(hour => {
            const key = `${date} ${hour}`;
            allHourlyData[key] = hourlyForDay[hour];
          });
          setHourlyUsage({...allHourlyData});
        });
      });
      
      setStats(statsRes);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching app usage data:', error);
      setLoading(false);
    }
  };

  // Consistent color mapping for apps
  const APP_COLORS = {
    'Chrome': { hex: '#4285F4', bg: 'bg-blue-500', text: 'text-blue-600' },
    'Firefox': { hex: '#FF7139', bg: 'bg-orange-500', text: 'text-orange-600' },
    'Excel': { hex: '#217346', bg: 'bg-green-600', text: 'text-green-700' },
    'Word': { hex: '#2B579A', bg: 'bg-blue-700', text: 'text-blue-800' },
    'PowerPoint': { hex: '#D24726', bg: 'bg-red-600', text: 'text-red-700' },
    'Outlook': { hex: '#0078D4', bg: 'bg-blue-600', text: 'text-blue-700' },
    'Teams': { hex: '#6264A7', bg: 'bg-indigo-600', text: 'text-indigo-700' },
    'Slack': { hex: '#4A154B', bg: 'bg-purple-800', text: 'text-purple-900' },
    'Code': { hex: '#007ACC', bg: 'bg-blue-500', text: 'text-blue-600' },
    'Spotify': { hex: '#1DB954', bg: 'bg-green-500', text: 'text-green-600' },
    'Notion': { hex: '#000000', bg: 'bg-gray-800', text: 'text-gray-900' },
    'Zoom': { hex: '#2D8CFF', bg: 'bg-blue-500', text: 'text-blue-600' },
    'Discord': { hex: '#5865F2', bg: 'bg-indigo-500', text: 'text-indigo-600' },
    'YouTube': { hex: '#FF0000', bg: 'bg-red-500', text: 'text-red-600' },
    'Acrobat': { hex: '#DC241F', bg: 'bg-red-600', text: 'text-red-700' },
    'OneNote': { hex: '#7719AA', bg: 'bg-purple-600', text: 'text-purple-700' },
  };

  const CHART_COLORS = [
    '#3B82F6', '#8B5CF6', '#EC4899', '#6366F1', '#10B981', '#F59E0B',
    '#EF4444', '#14B8A6', '#06B6D4', '#F97316', '#A855F7', '#84CC16',
  ];

  const getAppColor = (appNameOrIndex, type = 'bg') => {
    // Handle if it's an app name (string)
    if (typeof appNameOrIndex === 'string') {
      if (APP_COLORS[appNameOrIndex]) {
        return APP_COLORS[appNameOrIndex][type];
      }
      // Fallback to hash-based color for unknown app names
      const colors = {
        bg: ['bg-blue-500', 'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-green-500', 
             'bg-yellow-500', 'bg-red-500', 'bg-teal-500', 'bg-cyan-500', 'bg-orange-500'],
        hex: CHART_COLORS,
        text: ['text-blue-600', 'text-purple-600', 'text-pink-600', 'text-indigo-600', 'text-green-600',
               'text-yellow-600', 'text-red-600', 'text-teal-600', 'text-cyan-600', 'text-orange-600']
      };
      const hash = appNameOrIndex.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
      return colors[type][hash % colors[type].length];
    }
    
    // Handle if it's an index (number) - for backwards compatibility
    const colors = {
      bg: ['bg-blue-500', 'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-green-500', 
           'bg-yellow-500', 'bg-red-500', 'bg-teal-500', 'bg-cyan-500', 'bg-orange-500'],
      hex: CHART_COLORS,
      text: ['text-blue-600', 'text-purple-600', 'text-pink-600', 'text-indigo-600', 'text-green-600',
             'text-yellow-600', 'text-red-600', 'text-teal-600', 'text-cyan-600', 'text-orange-600']
    };
    return colors[type][appNameOrIndex % colors[type].length];
  };

  const getChartColor = (index) => {
    return CHART_COLORS[index % CHART_COLORS.length];
  };

  const formatMinutes = (minutes) => {
    if (minutes < 60) {
      return `${Math.round(minutes)}m`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  const renderTodayView = () => {
    const apps = Object.entries(todayUsage.usage || {});

    if (apps.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          <ComputerDesktopIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>No app usage data recorded yet today.</p>
          <p className="text-sm mt-2">Start using your apps and they'll appear here!</p>
        </div>
      );
    }

    // Prepare data for charts
    const topApps = apps.slice(0, 10);
    const barData = topApps.map(([app, minutes]) => ({
      app,
      minutes: Number(minutes.toFixed(1)),
      hours: Number((minutes / 60).toFixed(2))
    }));

    const pieData = topApps.map(([app, minutes]) => ({
      name: app,
      value: Number(minutes.toFixed(1))
    }));

    return (
      <div className="space-y-6">
        {/* Bar Chart + Pie Chart Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bar Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl p-6 shadow-lg border border-gray-200"
          >
            <div className="flex items-center space-x-2 mb-4">
              <ChartBarIcon className="w-6 h-6 text-blue-600" />
              <h3 className="text-lg font-bold text-gray-900">Time Spent by App</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="app" 
                  angle={-45} 
                  textAnchor="end" 
                  height={100}
                  tick={{ fontSize: 12 }}
                />
                <YAxis label={{ value: 'Minutes', angle: -90, position: 'insideLeft' }} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                  formatter={(value) => [`${value} min`, 'Time']}
                />
                <Bar dataKey="minutes" fill="#3B82F6" radius={[8, 8, 0, 0]}>
                  {barData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getChartColor(index)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Pie Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-xl p-6 shadow-lg border border-gray-200"
          >
            <div className="flex items-center space-x-2 mb-4">
              <ChartPieIcon className="w-6 h-6 text-purple-600" />
              <h3 className="text-lg font-bold text-gray-900">Usage Distribution</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getChartColor(index)} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value} min`} />
              </PieChart>
            </ResponsiveContainer>
          </motion.div>
        </div>

        {/* Detailed List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 shadow-lg border border-gray-200"
        >
          <h3 className="text-lg font-bold text-gray-900 mb-4">Detailed Breakdown</h3>
          <div className="space-y-3">
            {apps.map(([app, minutes], index) => {
              const percentage = (minutes / todayUsage.total_minutes) * 100;
              const appBgColor = getAppColor(app, 'bg');
              const appHexColor = getAppColor(app, 'hex');
              return (
                <div key={app} className="flex items-center space-x-3">
                  <div className={`w-10 h-10 ${appBgColor} rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}>
                    {app.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-gray-900">{app}</span>
                      <span className="text-sm text-gray-600">{formatMinutes(minutes)} ({percentage.toFixed(0)}%)</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        transition={{ duration: 0.8, delay: index * 0.05 }}
                        style={{ backgroundColor: appHexColor }}
                        className="h-full rounded-full"
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      </div>
    );
  };

  const renderWeekView = () => {
    const dates = Object.keys(weekUsage).sort().reverse();
    
    if (dates.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          <CalendarIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>No weekly app usage data available yet.</p>
        </div>
      );
    }

    // Prepare data for line chart (total time per day)
    const lineData = dates.slice().reverse().map(date => {
      const dayData = weekUsage[date];
      const dateObj = new Date(date);
      const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      return {
        date: dayName,
        minutes: dayData.total_minutes,
        hours: Number((dayData.total_minutes / 60).toFixed(1))
      };
    });

    // Prepare data for stacked area chart (top apps over time)
    const allApps = new Set();
    dates.forEach(date => {
      Object.keys(weekUsage[date].apps).forEach(app => allApps.add(app));
    });
    const topAppsOverall = Array.from(allApps).slice(0, 6);

    const stackedData = dates.slice().reverse().map(date => {
      const dayData = weekUsage[date].apps;
      const dateObj = new Date(date);
      const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
      const dataPoint = { date: dayName };
      topAppsOverall.forEach(app => {
        dataPoint[app] = dayData[app] ? Number(dayData[app].toFixed(1)) : 0;
      });
      return dataPoint;
    });

    return (
      <div className="space-y-6">
        {/* Line Chart - Total Daily Usage */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 shadow-lg border border-gray-200"
        >
          <div className="flex items-center space-x-2 mb-4">
            <ArrowTrendingUpIcon className="w-6 h-6 text-green-600" />
            <h3 className="text-lg font-bold text-gray-900">Daily Total Usage Trend</h3>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={lineData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis label={{ value: 'Minutes', angle: -90, position: 'insideLeft' }} />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                formatter={(value, name) => [`${value} min`, 'Total Time']}
              />
              <Line 
                type="monotone" 
                dataKey="minutes" 
                stroke="#10B981" 
                strokeWidth={3}
                dot={{ fill: '#10B981', r: 5 }}
                activeDot={{ r: 7 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Stacked Area Chart - Apps Over Time */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 shadow-lg border border-gray-200"
        >
          <div className="flex items-center space-x-2 mb-4">
            <ChartBarIcon className="w-6 h-6 text-blue-600" />
            <h3 className="text-lg font-bold text-gray-900">Top Apps Over Time</h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={stackedData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis label={{ value: 'Minutes', angle: -90, position: 'insideLeft' }} />
              <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }} />
              <Legend />
              {topAppsOverall.map((app, index) => (
                <Area
                  key={app}
                  type="monotone"
                  dataKey={app}
                  stackId="1"
                  stroke={getChartColor(index)}
                  fill={getChartColor(index)}
                  fillOpacity={0.8}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Daily Breakdown Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dates.map((date, dateIndex) => {
            const dayData = weekUsage[date];
            const apps = Object.entries(dayData.apps).sort((a, b) => b[1] - a[1]);
            const dateObj = new Date(date);
            const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
            const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            return (
              <motion.div
                key={date}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: dateIndex * 0.05 }}
                className="bg-gradient-to-br from-white to-gray-50 rounded-lg p-5 shadow-md border border-gray-200 hover:shadow-lg transition-shadow"
              >
                <div className="mb-3">
                  <h3 className="text-lg font-bold text-gray-900">{dayName}</h3>
                  <p className="text-sm text-gray-500">{dateStr}</p>
                  <p className="text-xs text-primary-600 font-semibold mt-1">Total: {formatMinutes(dayData.total_minutes)}</p>
                </div>
                <div className="space-y-2">
                  {apps.slice(0, 4).map(([app, minutes], index) => (
                    <div key={app} className="flex items-center justify-between text-sm">
                      <div className="flex items-center space-x-2">
                        <div className={`w-2 h-2 ${getAppColor(index)} rounded-full`} />
                        <span className="font-medium text-gray-700 truncate">{app}</span>
                      </div>
                      <span className="text-gray-600 font-semibold">{formatMinutes(minutes)}</span>
                    </div>
                  ))}
                  {apps.length > 4 && (
                    <p className="text-xs text-gray-400 mt-2">+ {apps.length - 4} more</p>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderHourlyView = () => {
    const hours = Object.keys(hourlyUsage).sort();
    
    if (hours.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          <ClockIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>No hourly data available yet.</p>
        </div>
      );
    }

    // Group hours by date
    const hoursByDate = {};
    hours.forEach(hourKey => {
      const datePart = hourKey.includes(' ') ? hourKey.split(' ')[0] : hourKey.split('_')[0];
      if (!hoursByDate[datePart]) {
        hoursByDate[datePart] = [];
      }
      hoursByDate[datePart].push(hourKey);
    });

    const dates = Object.keys(hoursByDate).sort().reverse().slice(0, 7); // Last 7 days

    return (
      <div className="space-y-6">
        {dates.map((date, dayIndex) => {
          const dayHours = hoursByDate[date].sort();
          const dateObj = new Date(date);
          const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
          const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

          // Calculate total for the day
          const dayTotal = dayHours.reduce((sum, hourKey) => {
            return sum + hourlyUsage[hourKey].total_minutes;
          }, 0);

          return (
            <motion.div
              key={date}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: dayIndex * 0.1 }}
              className="bg-white rounded-xl p-6 shadow-lg border border-gray-200"
            >
              {/* Day Header */}
              <div className="mb-6 pb-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">{dayName}</h3>
                    <p className="text-sm text-gray-500">{dateStr}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-primary-600">{formatMinutes(dayTotal)}</div>
                    <div className="text-xs text-gray-500">Total Time</div>
                  </div>
                </div>
              </div>

              {/* Hourly Grid */}
              <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-9 gap-3">
                {dayHours.map((hourKey, hourIndex) => {
                  const hourData = hourlyUsage[hourKey];
                  const timePart = hourKey.includes(' ') ? hourKey.split(' ')[1] : hourKey.split('_')[1];
                  const topApps = Object.entries(hourData.apps).sort((a, b) => b[1] - a[1]).slice(0, 3);
                  const topApp = topApps[0];
                  const topAppColor = topApp ? getAppColor(topApp[0], 'hex') : '#3B82F6';

                  return (
                    <motion.div
                      key={hourKey}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: dayIndex * 0.1 + hourIndex * 0.02 }}
                      className="rounded-lg p-3 border-2 hover:shadow-xl hover:scale-105 transition-all cursor-pointer group relative overflow-hidden"
                      style={{ 
                        borderColor: topAppColor,
                        background: `linear-gradient(135deg, ${topAppColor}15, white)`
                      }}
                    >
                      <div className="relative z-10">
                        {/* Time */}
                        <div className="text-lg font-bold mb-1" style={{ color: topAppColor }}>
                          {timePart}
                        </div>
                        <div className="text-xs text-gray-500 mb-3">60m active</div>
                        
                        {/* Top 3 Apps */}
                        <div className="space-y-2">
                          {topApps.map((appEntry, idx) => {
                            const [appName, minutes] = appEntry;
                            const appColor = getAppColor(appName, 'hex');
                            const appBgColor = getAppColor(appName, 'bg');
                            const percentage = (minutes / 60) * 100;
                            
                            return (
                              <div key={appName} className="space-y-1">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-1 flex-1">
                                    <div 
                                      className="w-2 h-2 rounded-full flex-shrink-0"
                                      style={{ backgroundColor: appColor }}
                                    ></div>
                                    <span className="text-xs font-medium truncate" style={{ color: appColor }}>
                                      {appName}
                                    </span>
                                  </div>
                                  <span className="text-xs text-gray-500 ml-1">{Math.round(minutes)}m</span>
                                </div>
                                {/* Progress bar */}
                                <div className="w-full bg-gray-200 rounded-full h-1">
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${percentage}%` }}
                                    transition={{ duration: 0.5, delay: dayIndex * 0.1 + hourIndex * 0.02 + idx * 0.1 }}
                                    className="h-full rounded-full"
                                    style={{ backgroundColor: appColor }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                      
                      {/* Accent corner */}
                      <div 
                        className="absolute top-0 right-0 w-8 h-8 opacity-20"
                        style={{ 
                          background: `linear-gradient(135deg, transparent 50%, ${topAppColor} 50%)`
                        }}
                      ></div>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold text-gray-900 mb-2">App Usage Insights</h1>
        <p className="text-gray-600">Track how you spend time across different applications</p>
      </motion.div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-lg"
          >
            <ClockIcon className="w-8 h-8 mb-2 opacity-80" />
            <p className="text-sm opacity-90 mb-1">Total Time Today</p>
            <p className="text-2xl font-bold">{formatMinutes(stats.total_time_today_minutes || 0)}</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white shadow-lg"
          >
            <ArrowTrendingUpIcon className="w-8 h-8 mb-2 opacity-80" />
            <p className="text-sm opacity-90 mb-1">Most Used Today</p>
            <p className="text-lg font-bold truncate">{stats.most_used_app_today || 'None'}</p>
            {stats.most_used_app_duration_minutes > 0 && (
              <p className="text-xs opacity-80">{formatMinutes(stats.most_used_app_duration_minutes)}</p>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white shadow-lg"
          >
            <ComputerDesktopIcon className="w-8 h-8 mb-2 opacity-80" />
            <p className="text-sm opacity-90 mb-1">Apps Tracked</p>
            <p className="text-2xl font-bold">{stats.unique_apps_tracked || 0}</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-6 text-white shadow-lg"
          >
            <ChartBarIcon className="w-8 h-8 mb-2 opacity-80" />
            <p className="text-sm opacity-90 mb-1">Avg Session</p>
            <p className="text-lg font-bold truncate">
              {stats.unique_apps_tracked > 0 
                ? formatMinutes((stats.total_time_today_minutes || 0) / stats.unique_apps_tracked) 
                : 'N/A'}
            </p>
          </motion.div>
        </div>
      )}

      {/* View Mode Tabs */}
      <div className="flex space-x-2 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setViewMode('today')}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            viewMode === 'today'
              ? 'bg-white text-primary-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Today
        </button>
        <button
          onClick={() => setViewMode('week')}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            viewMode === 'week'
              ? 'bg-white text-primary-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Past Week
        </button>
        <button
          onClick={() => setViewMode('hourly')}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            viewMode === 'hourly'
              ? 'bg-white text-primary-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Hourly
        </button>
      </div>

      {/* Content */}
      <div>
        {viewMode === 'today' && renderTodayView()}
        {viewMode === 'week' && renderWeekView()}
        {viewMode === 'hourly' && renderHourlyView()}
      </div>
    </div>
  );
};

export default AppUsage;

