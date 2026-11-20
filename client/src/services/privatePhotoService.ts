export interface PrivatePhotoPayload {
  mime: 'image/jpeg'
  image_base64: string
}

export const avatarPath = '/herlog/profile/avatar'
export const weightPhotoPath = (id: number) => `/herlog/weights/${id}/photo`
export const checkinPhotoPath = (id: number) => `/herlog/exercise/checkins/${id}/photo`
