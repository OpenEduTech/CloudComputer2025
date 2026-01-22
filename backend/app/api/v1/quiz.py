from fastapi import APIRouter, Depends, HTTPException
from app.api import deps
from app.models.user import UserResponse
from app.models.quiz import QuizCreate, QuizInDB, QuizSubmission, QuizResult, QuizBase
from app.core.database import db
from app.services.agents.question_generator import question_generator
from app.services.agents.grader import grader_agent
from bson import ObjectId
from typing import List

router = APIRouter()

@router.get("/history", response_model=List[QuizResult])
async def get_quiz_history(current_user: UserResponse = Depends(deps.get_current_user)):
    cursor = db.db.quiz_results.find({"user_id": str(current_user.id)})
    results = await cursor.to_list(length=100)
    return [QuizResult(**r) for r in results]

# Add route for getting a single result (used by frontend)
@router.get("/results/{result_id}")
async def get_quiz_result(
    result_id: str,
    current_user: UserResponse = Depends(deps.get_current_user)
):
    """Get a specific quiz result by ID"""
    try:
        result = await db.db.quiz_results.find_one({"_id": ObjectId(result_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")
        
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # 确保_id被正确转换为字符串
    if result and "_id" in result:
        result["_id"] = str(result["_id"])
    
    # 使用model_dump返回字典，确保id字段正确
    result_obj = QuizResult(**result)
    result_dict = result_obj.model_dump(by_alias=True)
    # 同时添加id字段（不使用别名）
    result_dict["id"] = str(result["_id"])
    return result_dict

@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    current_user: UserResponse = Depends(deps.get_current_user)
):
    """Get a quiz by ID"""
    try:
        quiz = await db.db.quiz.find_one({"_id": ObjectId(quiz_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")
        
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # 确保_id被正确转换为字符串
    if quiz and "_id" in quiz:
        quiz["_id"] = str(quiz["_id"])
    
    # 使用model_dump返回字典，确保id字段正确
    quiz_obj = QuizInDB(**quiz)
    result = quiz_obj.model_dump(by_alias=True)
    # 同时添加id字段（不使用别名）
    result["id"] = str(quiz["_id"])
    return result

@router.post("/generate")
async def generate_quiz(
    content: str,
    title: str,
    count: int = 5,
    current_user: UserResponse = Depends(deps.get_current_user)
):
    """
    从内容生成测验
    content: PDF解析后的文本内容
    title: 测验标题
    count: 题目数量
    """
    if not content or len(content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    # 获取用户年级信息
    user_grade = current_user.grade if hasattr(current_user, 'grade') and current_user.grade else "初中"
    
    # 生成题目（传入年级信息）
    questions = await question_generator.generate_questions(content, count, user_grade)
    
    quiz_data = {
        "title": title,
        "user_id": str(current_user.id),
        "questions": [q.model_dump() for q in questions]
    }
    
    new_quiz = await db.db.quiz.insert_one(quiz_data)
    created_quiz = await db.db.quiz.find_one({"_id": new_quiz.inserted_id})
    
    # 确保_id被正确转换为字符串
    if created_quiz and "_id" in created_quiz:
        created_quiz["_id"] = str(created_quiz["_id"])
    
    # 使用model_dump返回字典，确保id字段正确
    quiz_obj = QuizInDB(**created_quiz)
    result = quiz_obj.model_dump(by_alias=True)
    # 同时添加id字段（不使用别名）
    result["id"] = str(created_quiz["_id"])
    return result

@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    submission: QuizSubmission,
    current_user: UserResponse = Depends(deps.get_current_user)
):
    try:
        quiz = await db.db.quiz.find_one({"_id": ObjectId(quiz_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")
        
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    results = []
    # Map question IDs for easier lookup
    questions_map = {q["id"]: q for q in quiz["questions"]}
    
    for ans in submission.answers:
        q_data = questions_map.get(ans.question_id)
        if not q_data:
            continue
            
        from app.models.quiz import Question
        q_obj = Question(**q_data)
        grading = await grader_agent.grade_answer(q_obj, ans.user_answer)
        results.append(grading)
        
    # Simple overall analysis
    correct_count = sum(1 for r in results if r.is_correct)
    total = len(results)
    score_pct = (correct_count / total * 100) if total > 0 else 0
    
    overall_analysis = f"你的得分是 {score_pct:.1f}%。"
    if score_pct < 60:
        overall_analysis += "需要更多复习源材料。"
    else:
        overall_analysis += "对关键点有很好的理解！"
        
    result_data = {
        "quiz_id": quiz_id,
        "user_id": str(current_user.id),
        "submission": submission.model_dump(),
        "results": [r.model_dump() for r in results],
        "overall_analysis": overall_analysis
    }
    
    new_result = await db.db.quiz_results.insert_one(result_data)
    result_id = str(new_result.inserted_id)
    
    result_response = {
        "id": result_id,
        "quiz_id": quiz_id,
        "user_id": str(current_user.id),
        "submission": submission.model_dump(),
        "results": [r.model_dump() for r in results],
        "overall_analysis": overall_analysis
    }
    
    print("=" * 50)
    print("📤 submit_quiz 返回数据:")
    print(f"   result_id: {result_id}")
    print(f"   result_response: {result_response}")
    print("=" * 50)
    
    return result_response
