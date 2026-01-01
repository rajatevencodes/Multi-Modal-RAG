"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { ProjectsGrid } from "@/components/projects/ProjectsGrid";
import { CreateProjectModal } from "@/components/projects/CreateProjectModal";
import toast from "react-hot-toast";
import { apiClient } from "@/lib";
import { Project } from "@/types";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function DashboardPage() {
  const router = useRouter();

  // * Data States - What data we're tracking
  const [userProjectsList, setUserProjectsList] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // * UI States - How the interface looks and behaves
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false); // True when we're saving a new project

  // Clerk : https://clerk.com/docs/nextjs/reference/hooks/use-auth
  const { getToken, userId } = useAuth(); // getToken : JWT Token to attach with the API request's headers and userId: Clerk User ID

  /*
  ! Business Logic Functions - Core operations for this page:
  * - loadUserProjects: Get all projects from the server
  * - createNewProject: Make a new project with name and description
  * - removeProject: Delete a project by its ID
  */

  const loadUserProjects = useCallback(async () => {
    try {
      setIsLoadingProjects(true);
      setErrorMessage(null);
      const token = await getToken(); // Get user's authentication token from cookies
      const response = await apiClient.get("/api/project/list", token);
      const projectsData = response.data;
      // Ensure projectsData is always an array and has proper structure
      if (Array.isArray(projectsData)) {
        const validProjects = projectsData.map((project: any) => ({
          id: project.id || "",
          name: project.name || "Untitled Project",
          description: project.description || "",
          created_at: project.created_at || new Date().toISOString(),
          clerk_id: project.clerk_id || userId || "",
        }));
        setUserProjectsList(validProjects);
      } else {
        setUserProjectsList([]);
      }
      setIsLoadingProjects(false);
    } catch (error) {
      console.error("Error while loading projects:", error);
      toast.error("Failed to load projects. Please try again.");
      setErrorMessage("Failed to load projects. Please try again.");
    } finally {
      setIsLoadingProjects(false);
    }
  }, [getToken, userId]);

  const createNewProject = async (name: string, description: string) => {
    try {
      setErrorMessage(null);
      setIsCreatingProject(true);
      const token = await getToken();
      const response = await apiClient.post(
        "/api/project/create",
        { name, description },
        token
      );
      const newlyCreatedProject = response?.data;

      // Refresh the projects list from server to ensure consistency
      await loadUserProjects();
      setShowCreateModal(false);
      toast.success("Project created successfully");
    } catch (error) {
      console.error("Error while creating project:", error);
      setErrorMessage("Failed to create project. Please try again.");
      toast.error("Failed to create project. Please try again.");
    } finally {
      setIsCreatingProject(false);
    }
  };
  const removeProject = async (_projectId: string) => {
    try {
      setErrorMessage(null);
      const token = await getToken();
      await apiClient.delete(`/api/project/delete/${_projectId}`, token);

      // Remove the project from local state immediately
      setUserProjectsList((prevProjects) =>
        prevProjects.filter((project) => project.id !== _projectId)
      );

      toast.success("Project removed successfully");
    } catch (error) {
      console.error("Error while removing project:", error);
      setErrorMessage("Failed to remove project. Please try again.");
      toast.error("Failed to remove project. Please try again.");
    }
  };

  /*
  ! User Interaction Functions:
  * - navigateToProject: Go to a specific project page when clicked
  * - openCreateModal/closeCreateModal: Show/hide the new project form
  * - changeViewMode: Switch between grid and list view
  */

  const navigateToProject = (projectId: string) => {
    router.push(`/projects/${projectId}`);
  };

  const openCreateModal = () => {
    setShowCreateModal(true);
  };
  const closeCreateModal = () => {
    setShowCreateModal(false);
  };
  const changeViewMode = (mode: "grid" | "list") => {
    setViewMode(mode);
  };
  const filterProjects = userProjectsList.filter((project) => {
    return (
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // Load user's projects when the page first loads
  useEffect(() => {
    if (userId) {
      loadUserProjects();
    }
  }, [userId, loadUserProjects]);

  if (isLoadingProjects) {
    return <LoadingSpinner message="Project Unloading..." />;
  }

  return (
    <>
      <ProjectsGrid
        projects={filterProjects}
        loading={isLoadingProjects}
        error={errorMessage}
        searchQuery={searchQuery}
        viewMode={viewMode}
        onSearchChange={setSearchQuery}
        onViewModeChange={changeViewMode}
        onProjectClick={navigateToProject}
        onCreateProject={openCreateModal}
        onDeleteProject={removeProject}
      />
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={closeCreateModal}
        onCreateProject={createNewProject}
        isLoading={isCreatingProject}
      />
    </>
  );
}
