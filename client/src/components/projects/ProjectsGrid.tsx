"use client";

import { Plus, Search, Grid3X3, List, Folder, Trash2 } from "lucide-react";
import { Project } from "@/types";

interface ProjectsGridProps {
  projects: Project[];
  loading: boolean;
  error: string | null;
  searchQuery: string;
  viewMode: "grid" | "list";
  onSearchChange: (query: string) => void;
  onViewModeChange: (mode: "grid" | "list") => void;
  onProjectClick: (projectId: string) => void;
  onCreateProject: () => void;
  onDeleteProject: (projectId: string) => void;
}

export function ProjectsGrid({
  projects,
  loading,
  error,
  searchQuery,
  viewMode,
  onSearchChange,
  onViewModeChange,
  onProjectClick,
  onCreateProject,
  onDeleteProject,
}: ProjectsGridProps) {
  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white">
      {/* Header */}
      <div className="border-b border-gray-800/50 bg-[#0f0f0f]/95 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-6">
          {/* Top Row */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 sm:mb-6">
            <div>
              <h1 className="text-xl sm:text-2xl font-medium text-white tracking-tight">
                Projects
              </h1>
              <p className="text-gray-400 text-sm mt-1">
                {projects.length} project{projects.length !== 1 ? "s" : ""}
              </p>
            </div>

            <button
              onClick={onCreateProject}
              disabled={loading}
              className="bg-white hover:bg-gray-100 disabled:bg-gray-700 disabled:text-gray-500 text-black px-4 py-2.5 rounded-full flex items-center justify-center gap-2 transition-all duration-200 font-medium text-sm shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 disabled:transform-none w-full sm:w-auto"
            >
              <Plus size={16} />
              <span className="sm:inline">Create new</span>
            </button>
          </div>

          {/* Controls Row */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            {/* Search */}
            <div className="relative flex-1 sm:max-w-md">
              <Search
                size={16}
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500"
              />
              <input
                type="text"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                disabled={loading}
                className="w-full pl-10 pr-4 py-2.5 bg-gray-900/50 border border-gray-800 rounded-full focus:outline-none focus:ring-2 focus:ring-gray-700 focus:border-transparent placeholder-gray-500 text-white text-sm disabled:opacity-50 transition-all duration-200"
              />
            </div>

            {/* View Controls */}
            <div className="flex items-center justify-center sm:justify-end gap-2">
              {/* View Toggle */}
              <div className="flex items-center bg-gray-900/50 border border-gray-800 rounded-lg p-1">
                <button
                  onClick={() => onViewModeChange("grid")}
                  className={`p-2 sm:p-1.5 rounded transition-all duration-200 ${
                    viewMode === "grid"
                      ? "bg-gray-700 text-white"
                      : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  <Grid3X3 size={16} />
                </button>
                <button
                  onClick={() => onViewModeChange("list")}
                  className={`p-2 sm:p-1.5 rounded transition-all duration-200 ${
                    viewMode === "list"
                      ? "bg-gray-700 text-white"
                      : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  <List size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-4 sm:pt-6">
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            <span className="text-red-400 text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {projects.length === 0 ? (
          <div className="text-center py-12 sm:py-20 px-4">
            {searchQuery ? (
              // No search results
              <div className="max-w-md mx-auto">
                <div className="w-14 h-14 sm:w-16 sm:h-16 bg-gray-800 rounded-full mx-auto mb-4 sm:mb-6 flex items-center justify-center">
                  <Search size={20} className="text-gray-500 sm:w-6 sm:h-6" />
                </div>
                <h3 className="text-lg sm:text-xl font-medium text-white mb-3">
                  No projects found
                </h3>
                <p className="text-gray-400 mb-6 text-sm sm:text-base">
                  Try adjusting your search terms or create a new project
                </p>
                <button
                  onClick={() => onSearchChange("")}
                  className="text-gray-300 hover:text-white text-sm underline underline-offset-4"
                >
                  Clear search
                </button>
              </div>
            ) : (
              // No projects at all
              <div className="max-w-md mx-auto">
                <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-gray-800 to-gray-900 rounded-2xl mx-auto mb-4 sm:mb-6 flex items-center justify-center shadow-xl">
                  <Plus size={24} className="text-gray-400 sm:w-8 sm:h-8" />
                </div>
                <h3 className="text-xl sm:text-2xl font-medium text-white mb-3">
                  Create your first project
                </h3>
                <p className="text-gray-400 mb-6 sm:mb-8 leading-relaxed text-sm sm:text-base">
                  Projects help you organize your documents and conversations.
                  Start by creating your first project.
                </p>
                <button
                  onClick={onCreateProject}
                  className="bg-white hover:bg-gray-100 text-black px-4 sm:px-6 py-2.5 sm:py-3 rounded-full transition-all duration-200 font-medium shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 text-sm sm:text-base w-full sm:w-auto"
                >
                  Create your first project
                </button>
              </div>
            )}
          </div>
        ) : (
          // Projects Grid/List
          <div className="space-y-6">
            {/* Recent Projects Header */}
            <div>
              <h2 className="text-lg font-medium text-gray-300 mb-4">
                Recent projects
              </h2>

              {viewMode === "grid" ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
                  {projects.map((project, key) => (
                    <div
                      key={key}
                      onClick={() => onProjectClick(project.id)}
                      className="group bg-gray-900/50 hover:bg-gray-900/80 border border-gray-800 hover:border-gray-700 rounded-xl p-4 sm:p-6 cursor-pointer transition-all duration-200 hover:shadow-xl hover:-translate-y-1 relative touch-manipulation"
                    >
                      {/* Project Icon */}
                      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-gray-700 to-gray-800 rounded-xl mb-3 sm:mb-4 flex items-center justify-center shadow-lg group-hover:shadow-xl transition-all duration-200">
                        <Folder
                          size={20}
                          className="text-gray-400 sm:w-6 sm:h-6"
                        />
                      </div>

                      {/* Project Info */}
                      <div className="space-y-2">
                        <h3 className="font-medium text-white text-sm sm:text-base line-clamp-2 group-hover:text-gray-100 transition-colors">
                          {project.name}
                        </h3>

                        {project.description && (
                          <p className="text-gray-400 text-xs sm:text-sm line-clamp-2 leading-relaxed">
                            {project.description}
                          </p>
                        )}

                        <div className="pt-1 sm:pt-2">
                          <span className="text-xs text-gray-500">
                            {new Date(project.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      {/* Delete Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteProject(project.id);
                        }}
                        className="absolute top-3 right-3 sm:top-4 sm:right-4 p-2 sm:p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-all duration-200 opacity-0 group-hover:opacity-100 cursor-pointer hover:scale-110 touch-manipulation"
                        title="Delete project"
                      >
                        <Trash2 size={14} className="sm:w-3 sm:h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                // List View
                <div className="space-y-2">
                  {projects.map((project) => (
                    <div
                      key={project.id}
                      onClick={() => onProjectClick(project.id)}
                      className="group flex items-center gap-3 sm:gap-4 bg-gray-900/30 hover:bg-gray-900/60 border border-gray-800/50 hover:border-gray-700 rounded-lg p-3 sm:p-4 cursor-pointer transition-all duration-200 touch-manipulation"
                    >
                      {/* Icon */}
                      <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-gray-700 to-gray-800 rounded-lg flex items-center justify-center shrink-0">
                        <Folder
                          size={16}
                          className="text-gray-400 sm:w-5 sm:h-5"
                        />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-white text-sm sm:text-base truncate group-hover:text-gray-100 transition-colors">
                          {project.name}
                        </h3>
                        {project.description && (
                          <p className="text-gray-400 text-xs sm:text-sm truncate mt-1 hidden sm:block">
                            {project.description}
                          </p>
                        )}
                      </div>

                      {/* Date - Hidden on mobile, shown on larger screens */}
                      <div className="hidden sm:block text-xs text-gray-500 shrink-0 self-start">
                        {new Date(project.created_at).toLocaleDateString()}
                      </div>

                      {/* Delete Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteProject(project.id);
                        }}
                        className="p-2 sm:p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-all duration-200 opacity-0 group-hover:opacity-100 cursor-pointer hover:scale-110 touch-manipulation"
                        title="Delete project"
                      >
                        <Trash2 size={14} className="sm:w-3 sm:h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
