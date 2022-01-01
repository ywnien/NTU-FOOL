from NTU.cool import Cool, Fool

c = Cool()
f = Fool(c)

# Cool 爬資料
print('請選擇學期:')
print(f'目前: {c.semester}')
print(*c.semesters, sep=' | ')

new_semester = input('請選擇學期: ')
c.set_semester(new_semester)

c.update() # 更新該學期的所有課程內容

print('\n開始下載課程內容附件...')
print(*(c.courses[c.semester]), sep='\n')
search = input('請選擇課程: ')
c.download(search) # 先只下載一門課

# Fool 寫成 html
f.nav_update() # 更新導航列，只在註冊課程變動時需要 (如環安衛、加簽、退選、停修等等)
f.build()