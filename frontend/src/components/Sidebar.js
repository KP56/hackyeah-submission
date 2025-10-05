import React, { useState } from 'react';
import { 
  HomeIcon, 
  CogIcon, 
  EnvelopeIcon, 
  SparklesIcon,
  ExclamationTriangleIcon,
  WrenchScrewdriverIcon,
  ServerIcon,
  BoltIcon,
  ChatBubbleLeftRightIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';

const Sidebar = ({ activeTab, setActiveTab, isCollapsed, setIsCollapsed, windowWidth, mobileMenuOpen, setMobileMenuOpen }) => {
  const tabs = [
    { id: 'dashboard', name: 'Dashboard', icon: HomeIcon },
    { id: 'chat', name: 'Automation Chat', icon: ChatBubbleLeftRightIcon },
    { id: 'actions', name: 'Your Actions', icon: BoltIcon },
    { id: 'app-usage', name: 'App Usage', icon: ChartBarIcon },
    { id: 'backend', name: 'Backend Status', icon: ServerIcon },
    { id: 'smart-automation', name: 'Smart Automation', icon: SparklesIcon },
    { id: 'settings', name: 'Settings', icon: CogIcon },
    { id: 'email', name: 'Email Config', icon: EnvelopeIcon },
  ];

  return (
    <motion.div 
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={`bg-white shadow-lg border-r border-gray-200 transition-all duration-300 sidebar-container ${
        windowWidth < 768 
          ? `fixed inset-y-0 left-0 z-50 ${isCollapsed ? 'sidebar-fixed-width' : 'sidebar-fixed-width-expanded'} ${mobileMenuOpen ? 'transform translate-x-0' : 'transform -translate-x-full'}`
          : isCollapsed 
            ? 'fixed inset-y-0 left-0 z-50 sidebar-fixed-width' 
            : 'fixed inset-y-0 left-0 z-50 sidebar-fixed-width-expanded'
      }`}
    >
      <div className="flex flex-col h-full">
        <motion.div 
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 300 }}
          className="flex items-center justify-between h-16 px-4 border-b border-gray-200"
        >
          <AnimatePresence>
            {!isCollapsed && (
              <motion.h1 
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className="text-xl font-bold text-gray-900"
                whileHover={{ scale: 1.05 }}
              >
                ProcessBot
              </motion.h1>
            )}
          </AnimatePresence>
          
          <motion.button
            onClick={() => {
              setIsCollapsed(!isCollapsed);
              if (windowWidth < 768) {
                setMobileMenuOpen(false);
              }
            }}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            {isCollapsed ? (
              <ChevronRightIcon className="w-5 h-5 text-gray-600" />
            ) : (
              <ChevronLeftIcon className="w-5 h-5 text-gray-600" />
            )}
          </motion.button>
        </motion.div>
        
        <nav className="flex-1 px-4 py-6 space-y-2">
          <AnimatePresence>
            {tabs.map((tab, index) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              
              return (
                <motion.button
                  key={tab.id}
                  initial={{ x: -50, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  exit={{ x: -50, opacity: 0 }}
                  transition={{ 
                    delay: index * 0.05 + 0.1,
                    type: "spring",
                    stiffness: 400,
                    damping: 25
                  }}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center ${isCollapsed ? 'justify-center px-2' : 'px-4'} py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 border border-primary-200 shadow-sm'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                  whileHover={{ 
                    scale: 1.02,
                    x: 5,
                    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
                  }}
                  whileTap={{ scale: 0.98 }}
                  transition={{ 
                    type: "spring",
                    stiffness: 400,
                    damping: 25,
                    duration: 0.1
                  }}
                >
                  <motion.div
                    animate={isActive ? { 
                      scale: [1, 1.2, 1],
                      rotate: [0, 10, -10, 0]
                    } : {}}
                    transition={{ duration: 0.5 }}
                  >
                    <Icon className={`w-5 h-5 ${isCollapsed ? '' : 'mr-3'}`} />
                  </motion.div>
                  <AnimatePresence>
                    {!isCollapsed && (
                      <motion.span
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ 
                          opacity: 1, 
                          x: 0,
                          fontWeight: isActive ? [400, 600, 400] : 400
                        }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ duration: 0.2 }}
                      >
                        {tab.name}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  {isActive && (
                    <motion.div
                      initial={{ width: 0, opacity: 0 }}
                      animate={{ width: 4, opacity: 1 }}
                      exit={{ width: 0, opacity: 0 }}
                      className="ml-auto h-6 bg-primary-500 rounded-full"
                    />
                  )}
                </motion.button>
              );
            })}
          </AnimatePresence>
        </nav>
        
        <motion.div 
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.8, type: "spring", stiffness: 300 }}
          className="p-4 border-t border-gray-200"
        >
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="text-xs text-gray-500 text-center"
                whileHover={{ scale: 1.05 }}
              >
                Automation Assistant v1.0
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default Sidebar;
