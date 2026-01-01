"use client";
import { useParams } from "next/navigation";
import React, { useEffect, useState } from "react";
import { ConversationsList } from "@/components/projects/ConversationsList";
import { FileDetailsModal } from "@/components/projects/FileDetailsModal";
import { KnowledgeBaseSidebar } from "@/components/projects/KnowledgeBaseSidebar";
import { Project, Chat, ProjectDocument, ProjectSettings } from "@/types";
import { useAuth } from "@clerk/nextjs";
import { apiClient } from "@/lib";
import toast from "react-hot-toast";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { NotFound } from "@/components/ui/NotFound";
import { useRouter } from "next/navigation";

interface ProjectData {
  project: Project | null;
  chats: Chat[];
  documents: ProjectDocument[];
  settings: ProjectSettings | null;
}

const ProjectPage: React.FC = () => {
  const params = useParams();
  const router = useRouter();

  const projectId = params?.id as string;
  const { getToken, userId } = useAuth();

  // * Data States - What data we're tracking
  const [data, setData] = useState<ProjectData>({
    project: null,
    chats: [],
    documents: [],
    settings: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // * UI States - How the interface looks and behaves
  const [activeTab, setActiveTab] = useState<"documents" | "settings">(
    "documents"
  );
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null
  );
  const [isCreatingChat, setIsCreatingChat] = useState(false);

  /*
  ! Business Logic Functions - Core operations for this project:
  * - loadProjectData: Load all project data from the server

  * - handleCreateNewChat: Create a new conversation in this project
  * - handleDeleteChat: Remove a conversation from the project
  * - handleDocumentUpload: Process and add new documents to knowledge base
  * - handleDocumentDelete: Remove documents from knowledge base
  * - handleUrlAdd: Add web content to the knowledge base
  * - handleDraftSettings: Update project configuration locally
  * - handlePublishSettings: Save project settings to the server
  */

  useEffect(() => {
    const loadProjectData = async () => {
      if (!userId) return;

      try {
        setLoading(true);
        setError(null);

        const token = await getToken();

        const [projectRes, chatsRes, documentsRes, settingsRes] =
          await Promise.all([
            apiClient.get(`/api/project/${projectId}`, token),
            apiClient.get(`/api/project/${projectId}/chats`, token),
            apiClient.get(`/api/project/${projectId}/files`, token),
            apiClient.get(`/api/project/${projectId}/settings`, token),
          ]);

        setData({
          project: projectRes.data,
          chats: chatsRes.data,
          documents: documentsRes.data,
          settings: settingsRes.data,
        });
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch data";
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setLoading(false);
      }
    };
    loadProjectData();
  }, [userId, projectId, getToken]);

  useEffect(() => {
    const hasProcessingDocuments = data.documents.some(
      (doc) =>
        doc.processing_status &&
        !["completed", "failed"].includes(doc.processing_status)
    );

    if (!hasProcessingDocuments) {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const token = await getToken();
        const documentsRes = await apiClient.get(
          `/api/project/${projectId}/files`,
          token
        );

        setData((prev) => ({
          ...prev,
          documents: documentsRes.data,
        }));
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [data.documents, projectId, getToken]);

  const handleCreateNewChat = async () => {
    if (!userId) return;

    try {
      setIsCreatingChat(true);
      const token = await getToken();
      const chatNumber = Date.now() % 10000; // Generate a random chat number

      const response = await apiClient.post(
        "/api/chat/create",
        {
          title: `Chat #${chatNumber}`,
          project_id: projectId,
        },
        token
      );

      const savedChat = response?.data;

      router.push(`/projects/${projectId}/chats/${savedChat.id}`);

      // Update local state
      setData((prev) => ({
        ...prev,
        chats: [savedChat, ...prev.chats],
      }));

      toast.success("Chat Created successfully");
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to create chat";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsCreatingChat(false);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    if (!userId) return;
    try {
      const token = await getToken();
      await apiClient.delete(`/api/chat/delete/${chatId}`, token);

      setData((prev) => ({
        ...prev,
        chats: prev.chats.filter((chat) => chat.id !== chatId),
      }));
      toast.success("Chat deleted successfully");
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to delete chat";
      toast.error(errorMessage);
    }
  };

  const handleDocumentUpload = async (files: File[]) => {
    console.log("Upload files", files);
    if (!userId) return;

    try {
      console.log("Uploading files", files);
      const authToken = await getToken();
      const newlyUploadedDocuments: ProjectDocument[] = [];

      const fileUploadPromises = files.map(async (selectedFile) => {
        // Step 1: Request presigned URL from our server for S3 upload
        const presignedUrlPayload = {
          file_name: selectedFile.name,
          file_size: selectedFile.size,
          file_type: selectedFile.type,
        };

        const presignedUrlResponse = await apiClient.post(
          `/api/project/${projectId}/files/get-presigned-url`,
          presignedUrlPayload,
          authToken
        );

        const { presigned_url: s3PresignedUrl, s3_key: fileS3Key } =
          presignedUrlResponse.data;

        console.log("S3 Presigned URL received:", s3PresignedUrl);
        console.log("File S3 Key assigned:", fileS3Key);

        // Step 2: Upload the actual file directly to S3 using presigned URL
        const s3DirectUploadResponse = await apiClient.uploadToS3(
          s3PresignedUrl,
          selectedFile
        );

        if (!s3DirectUploadResponse.ok) {
          throw new Error(
            `S3 direct upload failed: ${s3DirectUploadResponse.status}`
          );
        }

        // Step 3: Tell our server the S3 upload is complete (triggers background processing)
        const uploadConfirmationPayload = {
          s3_key: fileS3Key,
        };

        const uploadConfirmationResponse = await apiClient.post(
          `/api/project/${projectId}/files/confirm-upload-to-s3`,
          uploadConfirmationPayload,
          authToken
        );

        const { file_update_result } = uploadConfirmationResponse.data;

        newlyUploadedDocuments.push(file_update_result);
      });

      await Promise.allSettled(fileUploadPromises);

      if (newlyUploadedDocuments.length > 0) {
        // Update the local state with the newly uploaded documents
        setData((previousData) => ({
          ...previousData,
          documents: [...previousData.documents, ...newlyUploadedDocuments],
        }));
        toast.success(
          `Successfully uploaded ${newlyUploadedDocuments.length} file(s)`
        );
      }
    } catch (uploadError) {
      const errorMessage =
        uploadError instanceof Error
          ? uploadError.message
          : "Failed to upload files";
      console.error("File upload error:", uploadError);
      toast.error(errorMessage);
    }
  };

  const handleDocumentDelete = async (documentId: string) => {
    console.log("Document Deleted");
    try {
      if (!userId) return;
      const token = await getToken();
      await apiClient.delete(
        `/api/project/${projectId}/files/delete/${documentId}`,
        token
      );
      setData((previousData) => ({
        ...previousData,
        documents: previousData.documents.filter(
          (doc) => doc.id !== documentId
        ),
      }));
      toast.success("Document deleted successfully");
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to delete document";
      toast.error(errorMessage);
    }
  };

  const handleUrlAdd = async (url: string) => {
    console.log("Add URL", url);

    try {
      if (!userId) return;
      const token = await getToken();
      const processUrlPayload = {
        url,
        project_id: projectId,
      };
      const processUrlResponse = await apiClient.post(
        `/api/project/${projectId}/files/process-url`,
        processUrlPayload,
        token
      );
      const { document_creation_result } = processUrlResponse.data;
      // Update Local state
      setData((previousData) => ({
        ...previousData,
        documents: [document_creation_result, ...previousData.documents],
      }));
      toast.success("Website is being processed...");
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to process URL";
      toast.error(errorMessage);
    }
  };

  // This function updates project settings temporarily (like a draft)
  // It doesn't save to the server yet - just updates what we see on screen
  const handleDraftSettings = (updates: Partial<ProjectSettings>) => {
    console.log("Update local state with draft settings", updates);

    // Update our local data state
    setData((prev) => {
      // If we already have some settings, merge the new changes with existing ones
      if (prev.settings) {
        return {
          ...prev, // Keep everything else the same
          settings: {
            ...prev.settings, // Keep existing settings
            ...updates, // Add/overwrite with new updates
          },
        };
      }

      // If no settings exist yet, we can't create them here
      // (we need the server to create them first)
      console.warn("No existing settings found to update");
      return prev; // Return unchanged data
    });
  };

  const handlePublishSettings = async () => {
    console.log("Make API call to publish settings");
    if (!userId || !data.settings) return;
    try {
      const token = await getToken();
      await apiClient.put(
        `/api/project/${projectId}/settings/update`,
        data.settings, // Send the current settings to the server
        token
      );
      toast.success("Settings published successfully");
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to publish settings";
      setError(errorMessage);
      toast.error(errorMessage);
    }
  };

  /*
  ! User Interaction Functions:
  * - handleChatClick: Navigate to a specific conversation when clicked
  * - handleOpenDocument: Show document details when user selects it
  */

  const handleChatClick = (chatId: string) => {
    console.log("Navigate to chat:", chatId);
    router.push(`/projects/${projectId}/chats/${chatId}`);
  };

  const handleOpenDocument = (documentId: string) => {
    console.log("Open document", documentId);
    setSelectedDocumentId(documentId);
  };

  const selectedDocument = selectedDocumentId
    ? data.documents.find((doc) => doc.id == selectedDocumentId)
    : null;

  if (loading) {
    return <LoadingSpinner message="Loading Project Data..." />;
  }

  if (error) {
    return <NotFound message={error} />;
  }

  return (
    <>
      <div className="flex h-screen bg-black gap-4 p-4">
        <ConversationsList
          project={data.project as Project}
          conversations={data.chats}
          error={null}
          loading={false}
          onCreateNewChat={handleCreateNewChat}
          onChatClick={handleChatClick}
          onDeleteChat={handleDeleteChat}
        />

        {/* KnowledgeBase Sidebar */}
        <KnowledgeBaseSidebar
          activeTab={activeTab}
          onSetActiveTab={setActiveTab}
          projectDocuments={data.documents}
          onDocumentUpload={handleDocumentUpload}
          onDocumentDelete={handleDocumentDelete}
          onOpenDocument={handleOpenDocument}
          onUrlAdd={handleUrlAdd}
          projectSettings={data.settings as ProjectSettings}
          settingsError={null}
          settingsLoading={false}
          onUpdateSettings={handleDraftSettings}
          onApplySettings={handlePublishSettings}
        />
      </div>
      {selectedDocument && (
        <FileDetailsModal
          document={selectedDocument}
          onClose={() => setSelectedDocumentId(null)}
        />
      )}
    </>
  );
};

export default ProjectPage;
